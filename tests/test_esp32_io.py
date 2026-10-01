"""TDD boundaries: physical pulse acquisition and real loopback HTTP."""
import asyncio
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / 'firmware' / 'esp32_micropython'


def load(name):
    spec = importlib.util.spec_from_file_location('esp32_' + name, ROOT / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Pin:
    OUT, IN = 1, 0
    def __init__(self, number, mode, value=0):
        self.number, self.state, self.values = number, value, []
    def value(self, value=None):
        if value is not None:
            self.state = value
            self.values.append(value)
        return self.state


def test_hcsr04_trigger_and_conversion_are_measured_not_random():
    sensor_module = load('hcsr04')
    sleeps, pulses = [], []
    def measure(pin, value, timeout):
        pulses.append((pin.number, value, timeout))
        return 5800
    sensor = sensor_module.HCSR04(pin_factory=Pin, pulse_us=measure, sleep_us=sleeps.append)
    assert sensor.read() == {'distance_cm': 100.0}
    assert sensor.trigger.number == 26 and sensor.echo.number == 27
    assert sensor.trigger.values == [0, 1, 0]
    assert sleeps == [2, 10]
    assert pulses == [(27, 1, 30000)]


@pytest.mark.parametrize('pulse', [-2, -1, 0, 58, 24000])
def test_sensor_timeout_and_out_of_range_are_not_zero_readings(pulse):
    module = load('hcsr04')
    sensor = module.HCSR04(pin_factory=Pin, pulse_us=lambda *args: pulse, sleep_us=lambda _: None)
    with pytest.raises(module.SensorReadError):
        sensor.read()


def test_sensor_stuck_high_is_bounded():
    module = load('hcsr04')
    sensor = module.HCSR04(pin_factory=Pin, pulse_us=lambda *args: 5800, sleep_us=lambda _: None)
    sensor.echo.state = 1
    with pytest.raises(module.SensorReadError):
        sensor.read()


@pytest.mark.parametrize('url', ['http://example.com/v1/telemetry',
    'https://user:pass@example.com/v1/telemetry', 'https://example.com/other',
    'https://example.com/v1/telemetry?token=x', 'https://a\r\nb/v1/telemetry'])
def test_transport_rejects_unsafe_or_wrong_endpoint(url):
    module = load('tlm_http')
    with pytest.raises(ValueError):
        module.HTTPTransport(url, 'x' * 43, ca_file='unused.pem')


def test_plain_http_is_opt_in_and_private_only():
    module = load('tlm_http')
    with pytest.raises(ValueError):
        module.HTTPTransport('http://8.8.8.8/v1/telemetry', 'x' * 43,
                             allow_insecure_http=True)
    transport = module.HTTPTransport('http://192.168.1.10:8000/v1/telemetry', 'x' * 43,
                                     allow_insecure_http=True)
    assert transport.host == '192.168.1.10'
    assert transport.port == 8000


def test_header_injection_in_token_is_rejected():
    module = load('tlm_http')
    with pytest.raises(ValueError):
        module.HTTPTransport('https://example.com/v1/telemetry', 'x' * 43 + '\r\n')


def run_response(response, expected_error=None):
    module = load('tlm_http')
    async def scenario():
        requests = []
        async def handler(reader, writer):
            try:
                headers = await reader.readuntil(b'\r\n\r\n')
                size = int(headers.split(b'Content-Length: ')[1].split(b'\r\n')[0])
                body = await reader.readexactly(size)
                requests.append((headers, body))
                writer.write(response)
                await writer.drain()
            finally:
                writer.close()
                await writer.wait_closed()
        server = await asyncio.start_server(handler, '127.0.0.1', 0)
        port = server.sockets[0].getsockname()[1]
        transport = module.HTTPTransport('http://127.0.0.1:%d/v1/telemetry' % port,
                                         'x' * 43, allow_insecure_http=True)
        try:
            if expected_error:
                with pytest.raises(expected_error):
                    await transport.post(b'{"test":1}')
            else:
                result = await transport.post(b'{"test":1}')
                assert requests[0][1] == b'{"test":1}'
                assert b'Authorization: Bearer ' + b'x' * 43 in requests[0][0]
                assert b'POST /v1/telemetry HTTP/1.1' in requests[0][0]
                return result
        finally:
            server.close()
            await server.wait_closed()
    return asyncio.run(scenario())


def test_actual_loopback_http_and_complete_ack_body():
    result = run_response(b'HTTP/1.1 201 Created\r\nContent-Length: 2\r\n'
                          b'Content-Type: application/json\r\n\r\n{}')
    assert result == (201, {'content-length': '2', 'content-type': 'application/json'}, b'{}')


def test_chunked_ack_is_supported_for_reverse_proxies():
    result = run_response(b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n'
                          b'Content-Type: application/json\r\n\r\n2\r\n{}\r\n0\r\n\r\n')
    assert result[0] == 200 and result[2] == b'{}'


@pytest.mark.parametrize('response', [
    b'HTTP/1.1 201 OK\r\nContent-Length: 99\r\n\r\n{}',
    b'HTTP/1.1 201 OK\r\nContent-Length: 999999999\r\n\r\n',
    b'HTTP/1.1 201 OK\r\nContent-Length: 2\r\nContent-Length: 3\r\n\r\n{}',
    b'HTTP/1.1 201 OK\r\nX-Huge: ' + b'a' * 8200 + b'\r\n\r\n',
    b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\nff\r\n{}',
])
def test_incomplete_ambiguous_or_large_responses_fail_closed(response):
    run_response(response, (OSError, ValueError, EOFError, asyncio.IncompleteReadError))


def test_tls_requires_ca_and_verification(tmp_path):
    module = load('tlm_http')
    with pytest.raises(ValueError):
        module.HTTPTransport('https://example.com/v1/telemetry', 'x' * 43)
    seen = {}
    class Context:
        def __init__(self, protocol):
            seen['protocol'] = protocol
        def load_verify_locations(self, cafile):
            seen['cafile'] = cafile
    class TLS:
        PROTOCOL_TLS_CLIENT, CERT_REQUIRED = 2, 2
        SSLContext = Context
    transport = module.HTTPTransport('https://example.com/v1/telemetry', 'x' * 43,
                                     ca_file='root.pem', ssl_module=TLS)
    assert transport.context.verify_mode == TLS.CERT_REQUIRED
    assert seen['cafile'] == 'root.pem'
