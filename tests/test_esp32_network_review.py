"""PR3 network regressions: real host threads, exact firmware, no external traffic."""
import asyncio
import importlib.util
import io
import json
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1] / 'firmware' / 'esp32_micropython'
DEVICE = '11111111-1111-4111-8111-111111111111'


def load(name, monkeypatch):
    spec = importlib.util.spec_from_file_location(name, ROOT / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def modules(monkeypatch):
    return {name: load(name, monkeypatch) for name in
            ('tlm_core', 'hcsr04', 'tlm_http', 'tlm_runtime', 'main')}


async def until(predicate):
    async def poll():
        while not predicate():
            await asyncio.sleep(0.005)
    await asyncio.wait_for(poll(), 3)


@pytest.mark.parametrize('host', [
    '010.0.0.1', '10.00.0.1', '10.0.00.1', '10.0.0.01',
    '0127.0.0.1', '127.00.0.1', '127.0.0.001', '192.168.001.1',
    '192.0168.1.1', '172.016.0.1', '172.16.00.1', '172.16.0.01',
    '8.0.0.1', '172.15.0.1', '172.32.0.1', '192.169.0.1',
    '10.0.0.256', '10.1', '0x0a.0.0.1', 'example.invalid',
])
def test_insecure_http_rejects_noncanonical_or_nonprivate_hosts(modules, host):
    with pytest.raises(ValueError):
        modules['tlm_http'].HTTPTransport('http://' + host + '/v1/telemetry',
                                        'x' * 43, allow_insecure_http=True)


@pytest.mark.parametrize('host', [
    '10.0.0.1', '10.255.255.254', '127.0.0.1', '192.168.0.1',
    '192.168.255.254', '172.16.0.1', '172.31.255.254',
])
def test_insecure_http_still_accepts_canonical_private_hosts(modules, host):
    result = modules['tlm_http'].HTTPTransport('http://' + host + '/v1/telemetry',
                                             'x' * 43, allow_insecure_http=True)
    assert result.host == host


@pytest.mark.parametrize('stop_kind', ['timeout', 'cancel'])
def test_worker_is_single_flight_and_discards_late_results(monkeypatch, stop_kind):
    net = load('tlm_net_worker', monkeypatch)
    started, release = threading.Event(), threading.Event()
    threads = []
    original_start = net._thread.start_new_thread

    def start(function, args):
        threads.append(True)
        return original_start(function, args)

    monkeypatch.setattr(net._thread, 'start_new_thread', start)

    def blocked():
        started.set()
        assert release.wait(5)
        return 'obsolete-result'

    async def scenario():
        worker = net.NetworkWorker()
        try:
            task = asyncio.create_task(worker.call(blocked, timeout=0.15 if stop_kind == 'timeout' else 2))
            await until(started.is_set)
            if stop_kind == 'cancel':
                task.cancel()
            with pytest.raises(asyncio.TimeoutError if stop_kind == 'timeout' else asyncio.CancelledError):
                await task
            for _ in range(5):
                with pytest.raises(OSError):
                    await worker.call(lambda: 'must-not-start')
            assert len(threads) == 1
            release.set()
            # Wait for the already-running operation, never replace its thread.
            await until(lambda: worker.idle())
            assert await worker.call(lambda: 'fresh-result') == 'fresh-result'
            assert len(threads) == 1
        finally:
            release.set()
            worker.close()
            await worker.wait_closed()
        with pytest.raises(OSError):
            await worker.call(lambda: 'closed')
    asyncio.run(scenario())


def test_worker_reports_failure_and_remains_usable(monkeypatch):
    net = load('tlm_net_worker', monkeypatch)

    def broken():
        raise OSError('test-only detail')

    async def scenario():
        worker = net.NetworkWorker()
        try:
            with pytest.raises(OSError, match='Network preparation failed'):
                await worker.call(broken)
            assert await worker.call(lambda x: x + 1, 41) == 42
        finally:
            worker.close()
            await worker.wait_closed()
    asyncio.run(scenario())


def test_close_during_running_job_is_bounded_and_late_result_is_ignored(monkeypatch):
    net = load('tlm_net_worker', monkeypatch)
    started, release = threading.Event(), threading.Event()

    def blocked():
        started.set()
        assert release.wait(5)
        return 'late'

    async def scenario():
        worker = net.NetworkWorker()
        task = asyncio.create_task(worker.call(blocked))
        try:
            await until(started.is_set)
            worker.close()
            with pytest.raises(OSError):
                await task
            with pytest.raises(asyncio.TimeoutError):
                await worker.wait_closed(timeout=0.05)
        finally:
            release.set()
            worker.close()
            await worker.wait_closed()
        assert worker.idle()
    asyncio.run(scenario())


class TLS:
    PROTOCOL_TLS_CLIENT, CERT_REQUIRED = 2, 2

    class SSLContext:
        def __init__(self, protocol):
            self.protocol = protocol

        def load_verify_locations(self, cafile):
            self.cafile = cafile


class Clock:
    def __init__(self, year=2026):
        self.start = time.monotonic()
        self.year = year

    def ticks_ms(self):
        return int((time.monotonic() - self.start) * 1000)

    @staticmethod
    def ticks_add(value, delta):
        return value + delta

    @staticmethod
    def ticks_diff(left, right):
        return left - right

    def gmtime(self, seconds=None):
        return time.gmtime(seconds) if seconds is not None else (self.year, 1, 1, 0, 0, 0, 0, 1)


@pytest.mark.parametrize('phase', ['dns', 'ntp'])
def test_blocked_network_preparation_keeps_exactly_one_persisted_message(modules, monkeypatch, tmp_path, phase):
    net = load('tlm_net_worker', monkeypatch)
    core, runtime, http, boot = [modules[n] for n in ('tlm_core', 'tlm_runtime', 'tlm_http', 'main')]
    # Accelerate cadence; a pending message must gate every later sensor read.
    monkeypatch.setattr(core, 'PERIOD_MS', 20)
    started, release = threading.Event(), threading.Event()
    worker_ids, rtc_calls, connects = [], [], []
    main_thread = threading.get_ident()

    def blocked(*args):
        worker_ids.append(threading.get_ident())
        started.set()
        assert release.wait(5)
        return '127.0.0.1' if phase == 'dns' else 1767225600

    monkeypatch.setattr(net, '_lookup_ipv4', blocked if phase == 'dns' else lambda *a: '127.0.0.1')
    monkeypatch.setattr(net, '_read_ntp_time', blocked)
    clock = Clock(year=2026 if phase == 'dns' else 2000)
    wlan = SimpleNamespace(isconnected=lambda: True)
    settings = {'NTP_HOST': 'ntp.example.invalid', 'WIFI_SSID': 'fixture', 'WIFI_PASSWORD': ''}
    queue = core.FileOutbox(str(tmp_path / 'outbox'), DEVICE)
    sensor = SimpleNamespace(read=lambda: {'distance_cm': 42})

    class RTC:
        def datetime(self, fields):
            assert threading.get_ident() == main_thread
            rtc_calls.append(fields)
            clock.year = fields[0]

    async def connector(host, port, ssl=None, server_hostname=None):
        connects.append((host, server_hostname))
        raise OSError('controlled offline transport')

    async def scenario():
        worker = net.NetworkWorker()
        transport = http.HTTPTransport('https://api.example.invalid/v1/telemetry', 'x' * 43,
                                       ca_file='fixture.pem', ssl_module=TLS,
                                       connector=connector, resolver=worker.resolve_ipv4)
        ready = boot.make_network_ready(settings, transport, wlan, clock, worker, RTC(), log=lambda *a: None)
        task = asyncio.create_task(runtime.run(queue, sensor, DEVICE, transport, ready, clock, log=lambda *a: None))
        try:
            await until(started.is_set)
            original = queue.peek()
            await asyncio.sleep(0.1)
            assert not release.is_set()
            assert queue.peek() == original
            assert len(list((tmp_path / 'outbox').glob('*.msg'))) == 1
            assert connects == [] and rtc_calls == []
            assert worker_ids and all(value != main_thread for value in worker_ids)
            release.set()
            await until(lambda: bool(connects))
            assert connects[0] == ('127.0.0.1', 'api.example.invalid')
            assert bool(rtc_calls) == (phase == 'ntp')
            assert queue.peek() == original
            packet = json.loads(queue.peek()[1])
            assert packet['sequence_no'] == 1
            assert packet['captured_at'] is None
        finally:
            release.set()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            worker.close()
            await worker.wait_closed()
    asyncio.run(scenario())


@pytest.mark.parametrize('resolved', ['127.0.0.1', '010.0.0.1', 'example.invalid', '::1', None])
def test_resolved_ip_validation_preserves_tls_hostname_and_host_header(modules, resolved):
    http = modules['tlm_http']
    calls, writes = [], []

    async def resolve(host, port):
        assert (host, port) == ('api.example.invalid', 8443)
        return resolved

    class Reader:
        def __init__(self):
            self.stream = io.BytesIO(b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\n{}')

        async def read(self, count):
            return self.stream.read(count)

        async def readexactly(self, count):
            return self.stream.read(count)

    class Writer:
        def write(self, data):
            writes.append(data)

        async def drain(self):
            pass

        def close(self):
            pass

        async def wait_closed(self):
            pass

    async def connector(host, port, ssl=None, server_hostname=None):
        calls.append((host, port, ssl, server_hostname))
        return Reader(), Writer()

    async def scenario():
        transport = http.HTTPTransport('https://api.example.invalid:8443/v1/telemetry', 'x' * 43,
                                       ca_file='fixture.pem', ssl_module=TLS,
                                       connector=connector, resolver=resolve)
        if resolved == '127.0.0.1':
            assert (await transport.post(b'{}'))[0] == 200
            assert calls == [(resolved, 8443, transport.context, 'api.example.invalid')]
            assert transport.context.verify_mode == TLS.CERT_REQUIRED
            assert b'Host: api.example.invalid:8443\r\n' in writes[0]
        else:
            with pytest.raises(ValueError):
                await transport.post(b'{}')
            assert not calls and not writes
    asyncio.run(scenario())


def test_numeric_http_never_uses_dns_resolver(modules):
    async def forbidden(*args):
        pytest.fail('A canonical numeric HTTP endpoint must bypass DNS')

    async def offline(host, port, **kwargs):
        assert host == '127.0.0.1'
        raise OSError('fixture offline')

    transport = modules['tlm_http'].HTTPTransport('http://127.0.0.1/v1/telemetry', 'x' * 43,
                                                 allow_insecure_http=True,
                                                 connector=offline, resolver=forbidden)
    with pytest.raises(OSError):
        asyncio.run(transport.post(b'{}'))


def test_ntp_helper_reads_time_without_mutating_rtc(monkeypatch):
    net = load('tlm_net_worker', monkeypatch)
    calls = []
    ntp = SimpleNamespace(time=lambda: calls.append(True) or 1767225600)
    monkeypatch.setitem(sys.modules, 'ntptime', ntp)
    assert net._read_ntp_time('ntp.example.invalid') == 1767225600
    assert calls == [True]
    assert ntp.host == 'ntp.example.invalid' and ntp.timeout == 2


@pytest.mark.parametrize('clock_year,ntp_host,outcome', [
    (2026, 'ntp.example.invalid', 'unused'), (2000, None, 'unused'),
    (2000, 'ntp.example.invalid', 'timeout'), (2000, 'ntp.example.invalid', 'error'),
])
def test_clock_readiness_fails_closed_and_ntp_retries_are_throttled(modules, clock_year, ntp_host, outcome):
    calls, rtc_calls = [], []

    async def get_time(host):
        calls.append(host)
        if outcome == 'timeout':
            raise asyncio.TimeoutError
        raise OSError('offline')

    clock = Clock(clock_year)
    ready = modules['main'].make_network_ready(
        {'NTP_HOST': ntp_host}, SimpleNamespace(secure=True),
        SimpleNamespace(isconnected=lambda: True), clock,
        SimpleNamespace(ntp_time=get_time), SimpleNamespace(datetime=rtc_calls.append), log=lambda *a: None)

    async def scenario():
        assert await ready() is (clock_year >= 2024)
        assert await ready() is (clock_year >= 2024)
    asyncio.run(scenario())
    assert calls == ([] if outcome == 'unused' else [ntp_host])
    assert rtc_calls == []


def test_late_ntp_answer_never_updates_rtc(modules, monkeypatch):
    net = load('tlm_net_worker', monkeypatch)
    started, release = threading.Event(), threading.Event()
    rtc_calls = []

    def blocked(host):
        started.set()
        assert release.wait(5)
        return 1767225600

    async def scenario():
        worker = net.NetworkWorker()

        async def short_ntp(host):
            return await worker.call(blocked, host, timeout=0.1)

        worker.ntp_time = short_ntp
        ready = modules['main'].make_network_ready(
            {'NTP_HOST': 'ntp.example.invalid'}, SimpleNamespace(secure=True),
            SimpleNamespace(isconnected=lambda: True), Clock(2000), worker,
            SimpleNamespace(datetime=rtc_calls.append), log=lambda *a: None)
        try:
            task = asyncio.create_task(ready())
            await until(started.is_set)
            assert await task is False
            release.set()
            await until(worker.idle)
            assert rtc_calls == []
        finally:
            release.set()
            worker.close()
            await worker.wait_closed()
    asyncio.run(scenario())


def test_lookup_requests_ipv4_stream_address_only(monkeypatch):
    net = load('tlm_net_worker', monkeypatch)
    seen = []

    def lookup(*args):
        seen.append(args)
        return [(2, 1, 6, '', ('127.0.0.1', 443))]

    monkeypatch.setitem(sys.modules, 'socket', SimpleNamespace(AF_INET=2, SOCK_STREAM=1, getaddrinfo=lookup))
    assert net._lookup_ipv4('api.example.invalid', 443) == '127.0.0.1'
    assert seen == [('api.example.invalid', 443, 2, 1)]


def test_boot_shares_one_worker_and_closes_it_on_runtime_failure(modules, monkeypatch, tmp_path):
    net = load('tlm_net_worker', monkeypatch)
    boot, core, http = [modules[n] for n in ('main', 'tlm_core', 'tlm_http')]
    real_worker, workers, triggered = net.NetworkWorker, [], []

    def new_worker():
        worker = real_worker()
        workers.append(worker)
        return worker

    class StopTest(Exception):
        pass

    async def run(queue, sensor, device_id, transport, ready, clock):
        assert len(workers) == 1
        assert transport.resolver.__self__ is workers[0]
        assert await ready() is True
        raise StopTest

    monkeypatch.setattr(net, 'NetworkWorker', new_worker)
    monkeypatch.setattr(boot, 'run', run)
    monkeypatch.setattr(boot, 'HTTPTransport', lambda *a, **k: http.HTTPTransport(*a, ssl_module=TLS, **k))
    monkeypatch.setattr(boot, 'FileOutbox', lambda path, device, capacity: core.FileOutbox(str(tmp_path / 'outbox'), device, capacity))
    monkeypatch.setattr(boot, 'HCSR04', lambda *args: SimpleNamespace(trigger=SimpleNamespace(value=triggered.append)))
    wlan = SimpleNamespace(active=lambda value: None, config=lambda **kwargs: None, isconnected=lambda: True)
    monkeypatch.setitem(sys.modules, 'network', SimpleNamespace(STA_IF=0, WLAN=lambda mode: wlan))
    monkeypatch.setitem(sys.modules, 'machine', SimpleNamespace(RTC=lambda: SimpleNamespace(datetime=lambda fields: None)))
    clock = Clock()
    for name in ('ticks_ms', 'ticks_add', 'ticks_diff', 'gmtime'):
        monkeypatch.setattr(time, name, getattr(clock, name), raising=False)
    monkeypatch.setattr(sys, 'platform', 'esp32')
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'config.secret.json').write_text(json.dumps({
        'TLM_DEVICE_ID': DEVICE, 'TLM_DEVICE_TOKEN': 'x' * 43,
        'TLM_API_URL': 'https://api.example.invalid/v1/telemetry',
        'WIFI_SSID': 'fixture', 'WIFI_PASSWORD': '',
    }))
    with pytest.raises(StopTest):
        boot.start()
    assert len(workers) == 1
    assert workers[0]._closed and workers[0]._stopped
    assert triggered[-1] == 0
