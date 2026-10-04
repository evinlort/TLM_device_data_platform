"""Runtime TDD: one persisted message is delivered before the next sample."""
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


def test_delivery_ack_log_includes_remaining_outbox_count(modules, tmp_path):
    _, _, runtime = modules
    q = make_queue(modules, tmp_path)
    logged = []

    class Transport:
        async def post(self, body):
            message = json.loads(body)
            ack = {'status': 'stored', 'device_id': DEVICE,
                   'message_id': message['message_id'],
                   'received_at': '2026-10-04T00:00:00Z'}
            return 201, {'content-type': 'application/json'}, json.dumps(ack).encode()

    async def scenario():
        async def ready():
            return True

        clock = type('Clock', (), {
            'ticks_ms': lambda self: 0,
            'ticks_add': lambda self, value, delta: value + delta,
            'ticks_diff': lambda self, left, right: -1,
        })()
        task = asyncio.create_task(runtime.run(
            q, Sensor(), DEVICE, Transport(), ready, clock,
            log=lambda *parts: logged.append(parts),
        ))
        while not logged:
            await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())
    assert logged == [('delivery_ack', 0)]


def test_timeout_retains_exact_packet_across_restart(modules, tmp_path):
    core, _, runtime = modules
    q = make_queue(modules, tmp_path)
    original = q.peek()[1]
    class Offline:
        async def post(self, body):
            raise OSError('Offline')
    assert asyncio.run(runtime.send_once(q, Offline())) == ('retry', None)
    assert core.FileOutbox(str(tmp_path / 'outbox'), DEVICE).peek()[1] == original


@pytest.mark.parametrize('failure,category', [
    (asyncio.TimeoutError('secret-token'), 'timeout'),
    (OSError(-203, 'secret-token'), 'os_error -203'),
    (EOFError('secret-token'), 'eof'),
    (ValueError('secret-token'), 'invalid_response'),
])
def test_delivery_error_log_is_sanitized_and_packet_retained(modules, tmp_path, failure, category):
    _, _, runtime = modules
    q = make_queue(modules, tmp_path)
    original = q.peek()[1]
    logged = []

    class Transport:
        async def post(self, body):
            raise failure

    assert asyncio.run(runtime.send_once(q, Transport(), log=lambda *parts: logged.append(parts))) == ('retry', None)
    assert logged == [('delivery_error', category)]
    assert 'secret-token' not in str(logged)
    assert q.peek()[1] == original


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


def test_pending_retry_blocks_new_sensor_reads(modules, monkeypatch, tmp_path):
    _, _, runtime = modules
    queue = make_queue(modules, tmp_path)
    original = queue.peek()[1]
    sensor_reads = []

    class CountingSensor:
        def read(self):
            sensor_reads.append(True)
            return {'distance_cm': 43.0}

    async def scenario():
        attempts = []

        class Offline:
            async def post(self, body):
                attempts.append(body)
                raise OSError('temporary')

        async def ready():
            return True

        monkeypatch.setattr(runtime, 'retry_seconds', lambda *args: 0)
        clock = type('Clock', (), {
            'ticks_ms': lambda self: 0,
            'ticks_add': lambda self, value, delta: value + delta,
            'ticks_diff': lambda self, left, right: left - right,
        })()
        task = asyncio.create_task(runtime.run(
            queue, CountingSensor(), DEVICE, Offline(), ready, clock,
            log=lambda *parts: None,
        ))
        while len(attempts) < 3:
            await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert attempts == [original, original, original]
        assert sensor_reads == []
        assert queue.count() == 1

    asyncio.run(scenario())


def test_ack_allows_exactly_one_next_sample_before_next_request(modules, monkeypatch, tmp_path):
    _, _, runtime = modules
    queue = make_queue(modules, tmp_path)
    sensor_reads = []

    async def scenario():
        second_post = asyncio.Event()
        posts = []

        class OneAckThenBlock:
            async def post(self, body):
                posts.append(body)
                message = json.loads(body)
                if len(posts) == 1:
                    ack = {'status': 'stored', 'device_id': DEVICE,
                           'message_id': message['message_id'],
                           'received_at': '2026-10-04T00:00:00Z'}
                    return 201, {'content-type': 'application/json'}, json.dumps(ack).encode()
                second_post.set()
                await asyncio.Event().wait()

        class CountingSensor:
            def read(self):
                sensor_reads.append(True)
                return {'distance_cm': 43.0}

        async def ready():
            return True

        monkeypatch.setattr(runtime, 'uuid4', lambda: STREAM)
        clock = type('Clock', (), {
            'ticks_ms': lambda self: 0,
            'ticks_add': lambda self, value, delta: value + delta,
            'ticks_diff': lambda self, left, right: left - right,
        })()
        task = asyncio.create_task(runtime.run(
            queue, CountingSensor(), DEVICE, OneAckThenBlock(), ready, clock,
            log=lambda *parts: None,
        ))
        await second_post.wait()
        assert len(posts) == 2
        assert sensor_reads == [True]
        assert json.loads(posts[1])['sequence_no'] == 1
        assert queue.count() == 1
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())


def test_second_runtime_is_rejected_and_guard_clears_after_cancel(modules, tmp_path):
    _, _, runtime = modules
    queue = make_queue(modules, tmp_path)

    async def scenario():
        entered = asyncio.Event()

        class Blocked:
            async def post(self, body):
                entered.set()
                await asyncio.Event().wait()

        async def ready():
            return True

        clock = type('Clock', (), {
            'ticks_ms': lambda self: 0,
            'ticks_add': lambda self, value, delta: value + delta,
            'ticks_diff': lambda self, left, right: left - right,
        })()
        first = asyncio.create_task(runtime.run(
            queue, Sensor(), DEVICE, Blocked(), ready, clock,
            log=lambda *parts: None,
        ))
        await entered.wait()
        with pytest.raises(RuntimeError, match='already running'):
            await runtime.run(queue, Sensor(), DEVICE, Blocked(), ready, clock)
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        assert not runtime.runtime_active()

        entered.clear()
        second = asyncio.create_task(runtime.run(
            queue, Sensor(), DEVICE, Blocked(), ready, clock,
            log=lambda *parts: None,
        ))
        await entered.wait()
        second.cancel()
        with pytest.raises(asyncio.CancelledError):
            await second
        assert not runtime.runtime_active()

    asyncio.run(scenario())


def test_fatal_delivery_preserves_message_and_allows_restart(modules, tmp_path):
    _, _, runtime = modules
    queue = make_queue(modules, tmp_path)
    original = queue.peek()[1]

    class Fatal:
        async def post(self, body):
            return 401, {}, b'{}'

    async def ready():
        return True

    clock = type('Clock', (), {
        'ticks_ms': lambda self: 0,
        'ticks_add': lambda self, value, delta: value + delta,
        'ticks_diff': lambda self, left, right: left - right,
    })()

    async def scenario():
        with pytest.raises(RuntimeError, match='operator attention'):
            await runtime.run(
                queue, Sensor(), DEVICE, Fatal(), ready, clock,
                log=lambda *parts: None,
            )
        assert not runtime.runtime_active()
        assert queue.peek()[1] == original

        entered = asyncio.Event()

        class Blocked:
            async def post(self, body):
                entered.set()
                await asyncio.Event().wait()

        second = asyncio.create_task(runtime.run(
            queue, Sensor(), DEVICE, Blocked(), ready, clock,
            log=lambda *parts: None,
        ))
        await entered.wait()
        second.cancel()
        with pytest.raises(asyncio.CancelledError):
            await second
        assert not runtime.runtime_active()
        assert queue.peek()[1] == original

    asyncio.run(scenario())
