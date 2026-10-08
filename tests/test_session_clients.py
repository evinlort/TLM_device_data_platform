"""Context capture and byte-for-byte mixed queue recovery on Linux and ESP32."""
import asyncio
import json
from pathlib import Path
import sys
from uuid import uuid4

import pytest

from tlm_device_data_platform.edge_agent import Outbox, HTTPSender
from tlm_device_data_platform.device_context import DeviceContext, ContextTracker
from tlm_device_data_platform.telemetry_v1 import TelemetryV1
from tlm_device_data_platform.telemetry_v2 import TelemetryV2, parse_message

FIRMWARE = Path(__file__).parents[1]/'firmware/esp32_micropython'
sys.path.insert(0, str(FIRMWARE))
import tlm_core
import tlm_runtime


def test_linux_context_cache_and_mixed_queue_survive_reboot(tmp_path):
    device, session = uuid4(), uuid4()
    queue = Outbox(tmp_path/'queue.sqlite3', device)
    v1 = TelemetryV1(device, uuid4(), uuid4(), 1, None,
                     {'test_sensor': 1}).to_bytes()
    queue.enqueue(v1)
    context = DeviceContext(device, session, 1)
    queue.save_context(context)
    v2 = TelemetryV2(device, uuid4(), uuid4(), 1, None, {
                     'test_sensor': 2}, session).to_bytes()
    queue.enqueue(v2)
    reopened = Outbox(queue.path, device)
    assert reopened.load_context() == context
    assert reopened.oldest()[1] == v1
    reopened.acknowledge(str(parse_message(v1).message_id))
    assert reopened.oldest()[1] == v2
    reopened.save_context(DeviceContext(device, None, 2))
    assert reopened.oldest()[1] == v2
    with pytest.raises(ValueError):
        reopened.save_context(context)


def test_first_context_required_and_offline_cache(tmp_path):
    device, session = uuid4(), uuid4()
    queue = Outbox(tmp_path/'queue.sqlite3', device)

    class Sender:
        offline = False

        def context(self, device):
            if self.offline:
                raise OSError('TEST offline')
            return DeviceContext(device, session, 1)
    sender = Sender()
    tracker = ContextTracker(queue, sender)
    with pytest.raises(RuntimeError):
        tracker.current()
    tracker.refresh()
    sender.offline = True
    tracker.refresh()
    assert tracker.current().session_id == session
    recovered = ContextTracker(Outbox(queue.path, device), sender)
    recovered.refresh()
    assert recovered.current().session_id == session


def test_esp32_v2_context_cache_and_mixed_queue(tmp_path):
    device, session = str(uuid4()), str(uuid4())
    queue = tlm_core.FileOutbox(str(tmp_path), device)
    legacy = tlm_core.make_message(device, str(uuid4()), 1, {
                                   'test_sensor': 1}, str(uuid4()))
    queue.enqueue(legacy)
    queue.save_context(
        {'device_id': device, 'session_id': session, 'revision': 1})

    class Sensor:
        def read(self):
            return {'test_sensor': 2}
    modern = tlm_runtime.sample_once(queue, Sensor(), device, str(uuid4()), 1,
                                     context=queue.load_context())
    assert parse_message(modern).session_id == __import__('uuid').UUID(session)
    recovered = tlm_core.FileOutbox(str(tmp_path), device)
    assert recovered.load_context()['session_id'] == session
    name, body = recovered.peek()
    assert body == legacy
    recovered.ack(name, body)
    assert recovered.peek()[1] == modern
    recovered.save_context(
        {'device_id': device, 'session_id': None, 'revision': 2})
    assert recovered.peek()[1] == modern


def test_startup_refreshes_cached_context_before_collection(tmp_path):
    device, old, new = uuid4(), uuid4(), uuid4()
    queue = Outbox(tmp_path/'queue.sqlite3', device)
    queue.save_context(DeviceContext(device, old, 1))

    class Sender:
        def context(self, device):
            return DeviceContext(device, new, 3)
    tracker = ContextTracker(queue, Sender())
    with pytest.raises(RuntimeError):
        tracker.current()
    tracker.refresh()
    assert tracker.current().session_id == new


def test_linux_context_refresh_does_not_block_collection(tmp_path):
    from threading import Event
    from tlm_device_data_platform.edge_agent import Delivery, run_agent
    device = uuid4()
    queue = Outbox(tmp_path/'independent.sqlite3', device)
    entered = Event()

    class Sender:
        calls = 0

        def context(self, device):
            self.calls += 1
            if self.calls > 1:
                entered.set()
                __import__('time').sleep(.25)
            return DeviceContext(device, None, 0)

        def send(self, body):
            return Delivery('ack')
    sender = Sender()
    tracker = ContextTracker(queue, sender)
    tracker.refresh()
    reads = []
    assert run_agent(queue, sender, lambda: reads.append(__import__('time').monotonic()) or {'test_sensor': 1},
                     interval=.02, count=3, context_tracker=tracker) == {}
    assert entered.is_set()
    assert reads[-1]-reads[0] < .2


def test_context_is_refreshed_after_detected_reconnection(tmp_path):
    device, old, new = uuid4(), uuid4(), uuid4()
    queue = Outbox(tmp_path/'reconnect.sqlite3', device)

    class Sender:
        offline = False
        session = old
        revision = 1

        def context(self, device):
            if self.offline:
                raise OSError('TEST offline')
            return DeviceContext(device, self.session, self.revision)
    sender = Sender()
    tracker = ContextTracker(queue, sender)
    tracker.refresh()
    sender.offline = True
    tracker.refresh()
    assert tracker.current().session_id == old
    tracker.observe_delivery()
    with pytest.raises(RuntimeError):
        tracker.current()
    sender.offline = False
    sender.session, sender.revision = new, 3
    tracker.refresh()
    assert tracker.current().session_id == new


def test_esp32_runtime_waits_for_context_and_switches_streams(tmp_path):
    device, first, second = str(uuid4()), str(uuid4()), str(uuid4())
    queue = tlm_core.FileOutbox(str(tmp_path/'runtime'), device)
    reads = []

    class Sensor:
        def read(self):
            reads.append(True)
            return {'test_sensor': 1}

    class Clock:
        def ticks_ms(self): return 0
        def ticks_add(self, a, b): return a+b
        def ticks_diff(self, a, b): return 0

    class Transport:
        session_aware = True
        contexts = 0
        packets = []

        async def fetch_context(self, device):
            self.contexts += 1
            assert self.contexts > len(self.packets)
            return {'device_id': device, 'session_id': first if self.contexts == 1 else second, 'revision': 1 if self.contexts == 1 else 3}

        async def post(self, body):
            self.packets.append(json.loads(body))
            m = self.packets[-1]
            return 201, {'content-type': 'application/json'}, json.dumps({'status': 'stored', 'device_id': device, 'message_id': m['message_id'], 'received_at': '2026-10-08T00:00:00Z'}).encode()
    transport = Transport()

    async def scenario():
        async def online(): return True
        task = asyncio.create_task(tlm_runtime.run(
            queue, Sensor(), device, transport, online, Clock(), log=lambda *a: None))
        while len(transport.packets) < 2:
            await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    asyncio.run(scenario())
    assert len(reads) == 2
    assert [m['session_id'] for m in transport.packets] == [first, second]
    assert transport.packets[0]['stream_id'] != transport.packets[1]['stream_id']
    assert [m['sequence_no'] for m in transport.packets] == [1, 1]


def test_esp32_missing_context_offline_performs_no_measurement(tmp_path):
    device = str(uuid4())
    queue = tlm_core.FileOutbox(str(tmp_path/'offline'), device)
    reads = []

    class Sensor:
        def read(self): reads.append(True); return {'test_sensor': 1}

    class Clock:
        def ticks_ms(self): return 0
        def ticks_add(self, a, b): return a+b
        def ticks_diff(self, a, b): return 0

    class Transport:
        session_aware = True

    async def scenario():
        async def offline(): return False
        task = asyncio.create_task(tlm_runtime.run(
            queue, Sensor(), device, Transport(), offline, Clock(), log=lambda *a: None))
        await asyncio.sleep(.02)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    asyncio.run(scenario())
    assert reads == []
    assert queue.peek() is None
