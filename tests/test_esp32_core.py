"""Host tests for the exact MicroPython source uploaded over USB."""
import importlib.util
import json
from pathlib import Path
from uuid import UUID

import pytest

ROOT = Path(__file__).resolve().parents[1] / "firmware" / "esp32_micropython"
DEVICE = "11111111-1111-4111-8111-111111111111"
STREAM = "22222222-2222-4222-8222-222222222222"
MESSAGE = "33333333-3333-4333-8333-333333333333"


@pytest.fixture
def core():
    spec = importlib.util.spec_from_file_location("esp32_core_test", ROOT / "tlm_core.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def packet(core, sequence=1):
    return core.make_message(DEVICE, STREAM, sequence, {"distance_cm": 100.0}, MESSAGE)


def test_uuid4_has_correct_version_and_variant(core):
    value = UUID(core.uuid4(lambda n: b"\x00" * n))
    assert value.version == 4
    assert str(value) == "00000000-0000-4000-8000-000000000000"


def test_message_uses_real_contract_and_null_unsynced_time(core):
    body = json.loads(packet(core))
    assert set(body) == {"schema_version", "device_id", "message_id", "stream_id",
                         "sequence_no", "captured_at", "payload"}
    assert body["payload"] == {"distance_cm": 100.0}
    assert body["captured_at"] is None
    assert body["sequence_no"] == 1


@pytest.mark.parametrize("payload", [{}, {"x": True}, {"x": None}, {"x": "1"},
                                      {"x": float("nan")}, {"x": float("inf")},
                                      {"x" * 65: 1}])
def test_invalid_readings_are_not_fabricated_or_serialized(core, payload):
    with pytest.raises(ValueError):
        core.make_message(DEVICE, STREAM, 1, payload, MESSAGE)


@pytest.mark.parametrize("sequence", [0, -1, True, 1.5, 2**63])
def test_invalid_sequence_is_rejected(core, sequence):
    with pytest.raises(ValueError):
        core.make_message(DEVICE, STREAM, sequence, {"distance_cm": 20}, MESSAGE)


def test_reopen_preserves_exact_bytes_and_fifo(core, tmp_path):
    q = core.FileOutbox(str(tmp_path / "q"), DEVICE, capacity=3)
    first = packet(core)
    second = packet(core, 2)
    q.enqueue(first)
    q.enqueue(second)
    reopened = core.FileOutbox(str(tmp_path / "q"), DEVICE, capacity=3)
    name, data = reopened.peek()
    assert data == first
    reopened.ack(name, data)
    assert reopened.peek()[1] == second


def test_full_queue_preserves_existing_data(core, tmp_path):
    q = core.FileOutbox(str(tmp_path / "q"), DEVICE, capacity=1)
    q.enqueue(packet(core))
    with pytest.raises(core.QueueFull):
        q.enqueue(packet(core, 2))
    assert q.peek()[1] == packet(core)


def test_quarantine_counts_against_capacity_and_keeps_bytes(core, tmp_path):
    q = core.FileOutbox(str(tmp_path / "q"), DEVICE, capacity=1)
    q.enqueue(packet(core))
    name, body = q.peek()
    q.quarantine(name)
    assert q.peek() is None
    with pytest.raises(core.QueueFull):
        q.enqueue(packet(core, 2))
    assert (tmp_path / "q" / name.replace(".msg", ".bad")).exists()
    assert body in (tmp_path / "q" / name.replace(".msg", ".bad")).read_bytes()


def test_wrong_device_cannot_take_over_old_queue(core, tmp_path):
    path = str(tmp_path / "q")
    core.FileOutbox(path, DEVICE).enqueue(packet(core))
    with pytest.raises(ValueError):
        core.FileOutbox(path, STREAM)


def test_corrupt_queue_fails_closed_without_deleting_data(core, tmp_path):
    q = core.FileOutbox(str(tmp_path / "q"), DEVICE)
    q.enqueue(packet(core))
    name, _ = q.peek()
    path = tmp_path / "q" / name
    path.write_bytes(path.read_bytes().replace(b"100.0", b"200.0"))
    with pytest.raises(core.QueueCorrupt):
        q.peek()
    assert path.exists()


def test_valid_interrupted_temp_write_is_recovered(core, tmp_path):
    path = tmp_path / "q"
    q = core.FileOutbox(str(path), DEVICE)
    q.enqueue(packet(core))
    name, body = q.peek()
    (path / name).rename(path / name.replace(".msg", ".tmp"))
    reopened = core.FileOutbox(str(path), DEVICE)
    assert reopened.peek()[1] == body


def test_ack_cannot_delete_different_bytes(core, tmp_path):
    q = core.FileOutbox(str(tmp_path / "q"), DEVICE)
    q.enqueue(packet(core))
    name, _ = q.peek()
    with pytest.raises(core.QueueCorrupt):
        q.ack(name, b"wrong")
    assert q.peek() is not None


@pytest.mark.parametrize("status,label", [(201, "stored"), (200, "duplicate")])
def test_matching_ack_only(core, status, label):
    ack = {"status": label, "device_id": DEVICE, "message_id": MESSAGE,
           "received_at": "2026-10-02T00:00:00+00:00"}
    assert core.response_action(status, json.dumps(ack).encode(), packet(core)) == "ack"
    ack["message_id"] = STREAM
    assert core.response_action(status, json.dumps(ack).encode(), packet(core)) == "retry"


@pytest.mark.parametrize("status,expected", [(400, "quarantine"), (409, "quarantine"),
    (413, "quarantine"), (422, "quarantine"), (401, "fatal"), (403, "fatal"),
    (301, "fatal"), (404, "fatal"), (415, "fatal"), (408, "retry"),
    (429, "retry"), (503, "retry"), (200, "retry"), (204, "retry")])
def test_status_policy(core, status, expected):
    assert core.response_action(status, b"{}", packet(core)) == expected


def test_schedule_is_ten_seconds_and_wrap_safe(core):
    wrap = 1 << 30
    add = lambda a, b: (a + b) % wrap
    diff = lambda a, b: (a - b + wrap // 2) % wrap - wrap // 2
    clock = core.Cadence(wrap - 5000, ticks_add=add, ticks_diff=diff)
    assert clock.due(wrap - 5000)
    assert not clock.due(4999)
    assert clock.due(5000)
    assert not clock.due(5000)
    assert clock.due(45000)
    assert not clock.due(45000)


def test_retry_after_is_bounded_and_never_spins(core):
    assert core.retry_seconds(0, "12") == 12
    assert core.retry_seconds(10, None) == 60
    assert core.retry_seconds(0, "999999999") == 300
    assert core.retry_seconds(0, "invalid") == 1
