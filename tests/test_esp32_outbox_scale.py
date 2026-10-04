"""Large legacy ESP32 outboxes must not require runtime directory scans."""
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1] / "firmware" / "esp32_micropython"
DEVICE = "11111111-1111-4111-8111-111111111111"
STREAM = "22222222-2222-4222-8222-222222222222"


@pytest.fixture
def core():
    spec = importlib.util.spec_from_file_location("esp32_outbox_scale", ROOT / "tlm_core.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def packet(core, sequence):
    message_id = "33333333-3333-4333-8333-%012d" % sequence
    return core.make_message(
        DEVICE, STREAM, sequence, {"distance_cm": 100.0}, message_id
    )


def legacy_record(core, directory, index, suffix="msg"):
    body = packet(core, index)
    name = "%016d.%s" % (index, suffix)
    (directory / name).write_bytes(core._digest(body) + b"\n" + body)
    return name, body


def legacy_outbox(core, tmp_path, size, suffixes=None):
    directory = tmp_path / "outbox"
    directory.mkdir()
    (directory / "owner").write_bytes(DEVICE.encode())
    suffixes = suffixes or {}
    records = {}
    for index in range(1, size + 1):
        records[index] = legacy_record(
            core, directory, index, suffixes.get(index, "msg")
        )
    return directory, records


def forbid_directory_scan(monkeypatch, core):
    def forbidden(*args, **kwargs):
        raise AssertionError("runtime operation scanned the whole outbox")

    monkeypatch.setattr(core.os, "listdir", forbidden)
    if hasattr(core.os, "scandir"):
        monkeypatch.setattr(core.os, "scandir", forbidden)
    if hasattr(core.os, "ilistdir"):
        monkeypatch.setattr(core.os, "ilistdir", forbidden)


@pytest.mark.parametrize("size", [400, 512, 1000])
def test_large_legacy_outbox_runtime_operations_do_not_rescan_directory(
    core, monkeypatch, tmp_path, size
):
    directory, records = legacy_outbox(core, tmp_path, size)
    queue = core.FileOutbox(str(directory), DEVICE, capacity=size + 2)
    forbid_directory_scan(monkeypatch, core)

    first_name, first_body = queue.peek()
    assert (first_name, first_body) == records[1]

    queue.enqueue(packet(core, size + 1))
    assert (directory / ("%016d.msg" % (size + 1))).exists()

    queue.ack(first_name, first_body)
    assert not (directory / first_name).exists()
    second_name, second_body = queue.peek()
    assert (second_name, second_body) == records[2]

    queue.quarantine(second_name)
    assert not (directory / second_name).exists()
    assert (directory / second_name.replace(".msg", ".bad")).exists()
    assert queue.peek() == records[3]


def test_large_legacy_outbox_queue_full_does_not_rescan_directory(
    core, monkeypatch, tmp_path
):
    directory, records = legacy_outbox(core, tmp_path, 512)
    queue = core.FileOutbox(str(directory), DEVICE, capacity=512)
    forbid_directory_scan(monkeypatch, core)

    with pytest.raises(core.QueueFull):
        queue.enqueue(packet(core, 513))
    assert queue.peek() == records[1]
    assert len(tuple(directory.glob("*.msg"))) == 512


def test_large_legacy_outbox_recovers_interrupted_write_without_listdir(
    core, monkeypatch, tmp_path
):
    directory, records = legacy_outbox(core, tmp_path, 1000, {1000: "tmp"})
    monkeypatch.setattr(
        core.os,
        "listdir",
        lambda *args, **kwargs: pytest.fail("startup materialized the directory"),
    )

    queue = core.FileOutbox(str(directory), DEVICE, capacity=1001)

    assert queue.peek() == records[1]
    assert not (directory / records[1000][0]).exists()
    assert (directory / records[1000][0].replace(".tmp", ".msg")).exists()


def test_sparse_legacy_layout_preserves_order_tail_count_and_quarantine(
    core, monkeypatch, tmp_path
):
    directory = tmp_path / "outbox"
    directory.mkdir()
    (directory / "owner").write_bytes(DEVICE.encode())
    first = legacy_record(core, directory, 1)
    legacy_record(core, directory, 2, "bad")
    fifth = legacy_record(core, directory, 5)
    queue = core.FileOutbox(str(directory), DEVICE, capacity=4)
    forbid_directory_scan(monkeypatch, core)

    assert queue.peek() == first
    queue.ack(*first)
    assert queue.peek() == fifth
    queue.enqueue(packet(core, 6))
    assert (directory / "0000000000000006.msg").exists()
    queue.quarantine(*queue.peek()[:1])
    assert queue.peek()[0] == "0000000000000006.msg"


def test_unexpected_file_still_fails_closed_during_streaming_scan(core, tmp_path):
    directory, _ = legacy_outbox(core, tmp_path, 400)
    unexpected = directory / "notes.txt"
    unexpected.write_text("preserve me")

    with pytest.raises(core.QueueCorrupt, match="Unexpected queue file"):
        core.FileOutbox(str(directory), DEVICE, capacity=512)
    assert unexpected.read_text() == "preserve me"
