"""Runtime TDD: queue first, exact replay, ACK and independent sampling."""
import asyncio
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / 'firmware' / 'esp32_micropython'
DEVICE = '11111111-1111-4111-8111-111111111111'
STREAM = '22222222-2222-4222-8222-222222222222'
MESSAGE = '33333333-3333-4333-8333-333333333333'


@pytest.fixture
def modules(monkeypatch):
    loaded = []
    for name in ('tlm_core', 'hcsr04', 'tlm_runtime'):
        spec = importlib.util.spec_from_file_location(name, ROOT / (name + '.py'))
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, name, module)
        spec.loader.exec_module(module)
        loaded.append(module)
    return loaded


class Sensor:
    def read(self):
        return {'distance_cm': 42.0}


def make_queue(modules, tmp_path):
    core, _, runtime = modules
    queue = core.FileOutbox(str(tmp_path / 'outbox'), DEVICE)
    runtime.sample_once(queue, Sensor(), DEVICE, STREAM, 1, lambda: MESSAGE)
    return queue


def test_sample_is_persisted_before_any_transport_call(modules, tmp_path):
    q = make_queue(modules, tmp_path)
    body = json.loads(q.peek()[1])
    assert body['payload'] == {'distance_cm': 42.0}
    assert body['message_id'] == MESSAGE


def test_sensor_error_does_not_enqueue_fake_zero(modules, tmp_path):
    core, driver, runtime = modules
    q = core.FileOutbox(str(tmp_path / 'outbox'), DEVICE)
    class Broken:
        def read(self):
            raise driver.SensorReadError('No echo')
    with pytest.raises(driver.SensorReadError):
        runtime.sample_once(q, Broken(), DEVICE, STREAM, 1, lambda: MESSAGE)
    assert q.peek() is None


@pytest.mark.parametrize('status,label', [(201, 'stored'), (200, 'duplicate')])
def test_verified_ack_removes_only_saved_message(modules, tmp_path, status, label):
    _, _, runtime = modules
    q = make_queue(modules, tmp_path)
    original = q.peek()[1]
    class Transport:
        async def post(self, body):
            assert body == original
            ack = {'status': label, 'device_id': DEVICE, 'message_id': MESSAGE,
                   'received_at': '2026-10-02T00:00:00Z'}
            return status, {'content-type': 'application/json'}, json.dumps(ack).encode()
    assert asyncio.run(runtime.send_once(q, Transport())) == ('ack', None)
    assert q.peek() is None


def test_timeout_retains_exact_packet_across_restart(modules, tmp_path):
    core, _, runtime = modules
    q = make_queue(modules, tmp_path)
    original = q.peek()[1]
    class Offline:
        async def post(self, body):
            raise OSError('Offline')
    assert asyncio.run(runtime.send_once(q, Offline())) == ('retry', None)
    assert core.FileOutbox(str(tmp_path / 'outbox'), DEVICE).peek()[1] == original


@pytest.mark.parametrize('status,expected', [(409, 'quarantine'), (401, 'fatal'),
    (503, 'retry'), (302, 'fatal'), (429, 'retry')])
def test_failure_actions_preserve_or_quarantine_without_ack(modules, tmp_path, status, expected):
    _, _, runtime = modules
    q = make_queue(modules, tmp_path)
    class Transport:
        async def post(self, body):
            return status, {'retry-after': '9'}, b'{}'
    assert asyncio.run(runtime.send_once(q, Transport())) == (expected, '9')
    assert (q.peek() is None) == (expected == 'quarantine')


def test_new_boot_stream_does_not_rewrite_old_queue(modules, tmp_path):
    core, _, runtime = modules
    q = make_queue(modules, tmp_path)
    old = q.peek()[1]
    q = core.FileOutbox(str(tmp_path / 'outbox'), DEVICE)
    runtime.sample_once(q, Sensor(), DEVICE, MESSAGE, 1, lambda: STREAM)
    name, body = q.peek()
    assert body == old
    q.ack(name, body)
    assert json.loads(q.peek()[1])['stream_id'] == MESSAGE


def test_slow_transport_does_not_block_sampling_coroutine(modules, tmp_path):
    core, _, runtime = modules
    q = make_queue(modules, tmp_path)
    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()
        class Slow:
            async def post(self, body):
                entered.set()
                await release.wait()
                raise OSError('temporary')
        task = asyncio.create_task(runtime.send_once(q, Slow()))
        await entered.wait()
        runtime.sample_once(q, Sensor(), DEVICE, STREAM, 2, lambda: STREAM)
        assert len(list((tmp_path / 'outbox').glob('*.msg'))) == 2
        release.set()
        assert await task == ('retry', None)
    asyncio.run(scenario())
