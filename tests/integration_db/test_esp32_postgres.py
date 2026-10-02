"""Execute the uploaded firmware source on the host with real API/PostgreSQL.

Only the physical echo pulse is replaced by an explicitly configured fixture.
The serializer, flash queue, HTTP transport and ACK handling are firmware code.
"""
import asyncio
import importlib.util
import json
import sys
from pathlib import Path
from uuid import uuid4

import pytest

from tlm_device_data_platform.telemetry_v1 import TelemetryV1

pytestmark = pytest.mark.database
ROOT = Path(__file__).resolve().parents[2]

# Reuse the existing isolated-role database fixture without copying its security rules.
_spec = importlib.util.spec_from_file_location(
    "esp32_database_helpers", Path(__file__).with_name("test_ingestion_postgres.py")
)
_helpers = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_helpers)
database = _helpers.database


@pytest.fixture
def firmware(monkeypatch):
    modules = {}
    for name in ("tlm_core", "hcsr04", "tlm_http", "tlm_runtime"):
        spec = importlib.util.spec_from_file_location(
            name, ROOT / "firmware" / "esp32_micropython" / (name + ".py")
        )
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, name, module)
        spec.loader.exec_module(module)
        modules[name] = module
    return modules


class TestPin:
    __test__ = False
    IN, OUT = 0, 1

    def __init__(self, number, mode, value=0):
        self.state = value

    def value(self, value=None):
        if value is not None:
            self.state = value
        return self.state


def sample(firmware, database, directory):
    core = firmware["tlm_core"]
    queue = core.FileOutbox(str(directory), str(database.message.device_id))
    sensor = firmware["hcsr04"].HCSR04(
        pin_factory=TestPin, pulse_us=lambda *args: 5800,
        sleep_us=lambda duration: None,
    )
    body = firmware["tlm_runtime"].sample_once(
        queue, sensor, str(database.message.device_id), str(uuid4()), 1
    )
    # Compare against the real server validator, not a duplicated fixture schema.
    message = TelemetryV1.parse(body)
    assert dict(message.payload) == {"distance_cm": 100.0}
    assert message.captured_at is None
    return queue, body, message


def test_esp32_reopened_queue_crosses_real_http_database_and_ack(database, firmware, tmp_path):
    directory = tmp_path / "outbox"
    _, body, message = sample(firmware, database, directory)
    queue = firmware["tlm_core"].FileOutbox(str(directory), str(message.device_id))
    with _helpers.serve(database.repository) as url:
        transport = firmware["tlm_http"].HTTPTransport(
            url, database.token, allow_insecure_http=True
        )
        assert asyncio.run(firmware["tlm_runtime"].send_once(queue, transport)) == ("ack", None)
    assert queue.peek() is None
    row = database.admin.execute(
        "SELECT message_id, stream_id, sequence_no, captured_at, payload "
        "FROM tlm.telemetry_messages WHERE device_id = %s",
        (message.device_id,),
    ).fetchone()
    assert row == (message.message_id, message.stream_id, 1, None, {"distance_cm": 100.0})


def test_esp32_lost_ack_replays_original_packet_without_duplicate(database, firmware, tmp_path):
    directory = tmp_path / "outbox"
    queue, body, message = sample(firmware, database, directory)
    with _helpers.serve(database.repository) as url:
        transport = firmware["tlm_http"].HTTPTransport(
            url, database.token, allow_insecure_http=True
        )
        # The server commits, but the device never processes this first ACK.
        status, _, first_ack = asyncio.run(transport.post(body))
        assert status == 201
        queue = firmware["tlm_core"].FileOutbox(str(directory), str(message.device_id))
        assert queue.peek()[1] == body
        assert asyncio.run(firmware["tlm_runtime"].send_once(queue, transport)) == ("ack", None)
    assert queue.peek() is None
    rows = database.admin.execute(
        "SELECT received_at, payload FROM tlm.telemetry_messages WHERE device_id = %s",
        (message.device_id,),
    ).fetchall()
    assert len(rows) == 1
    assert rows[0][0].isoformat() == json.loads(first_ack)["received_at"]
    assert rows[0][1] == {"distance_cm": 100.0}


def test_esp32_wrong_device_stops_delivery_and_preserves_packet(database, firmware, tmp_path):
    core = firmware["tlm_core"]
    other = str(database.other_device)
    queue = core.FileOutbox(str(tmp_path / "outbox"), other)
    body = core.make_message(other, str(uuid4()), 1, {"distance_cm": 100.0}, str(uuid4()))
    queue.enqueue(body)
    with _helpers.serve(database.repository) as url:
        transport = firmware["tlm_http"].HTTPTransport(
            url, database.token, allow_insecure_http=True
        )
        assert asyncio.run(firmware["tlm_runtime"].send_once(queue, transport)) == ("fatal", None)
    assert queue.peek()[1] == body
    assert database.admin.execute(
        "SELECT count(*) FROM tlm.telemetry_messages WHERE device_id IN (%s, %s)",
        (database.message.device_id, database.other_device),
    ).fetchone()[0] == 0
