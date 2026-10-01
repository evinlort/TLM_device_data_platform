"""ESP32 MicroPython 1.29.0 boot entry point. Copy as /main.py using USB."""
import asyncio
import json

from tlm_core import FileOutbox, canonical_uuid
from tlm_http import _endpoint, _TOKEN_CHARS, HTTPTransport
from hcsr04 import HCSR04
from tlm_runtime import run


def validate_config(settings):
    required = ('TLM_DEVICE_ID', 'TLM_DEVICE_TOKEN', 'TLM_API_URL', 'WIFI_SSID', 'WIFI_PASSWORD')
    defaults = {'ALLOW_INSECURE_HTTP': False, 'TRIG_PIN': 26, 'ECHO_PIN': 27,
                'OUTBOX_CAPACITY': 512, 'OUTBOX_PATH': '/tlm-outbox',
                'CA_FILE': 'ca.pem', 'NTP_HOST': 'pool.ntp.org'}
    if not isinstance(settings, dict) or any(key not in settings for key in required):
        raise ValueError('Missing device configuration')
    if any(key not in required and key not in defaults for key in settings):
        raise ValueError('Unknown setting; database credentials must never be on the device')
    result = dict(defaults)
    result.update(settings)
    result['TLM_DEVICE_ID'] = canonical_uuid(result['TLM_DEVICE_ID'])
    token = result['TLM_DEVICE_TOKEN']
    if (not isinstance(token, str) or not 43 <= len(token) <= 128
            or any(c not in _TOKEN_CHARS for c in token)):
        raise ValueError('Invalid device token')
    if type(result['ALLOW_INSECURE_HTTP']) is not bool:
        raise ValueError('ALLOW_INSECURE_HTTP must be a JSON boolean')
    _endpoint(result['TLM_API_URL'], result['ALLOW_INSECURE_HTTP'])
    ssid, password = result['WIFI_SSID'], result['WIFI_PASSWORD']
    if not isinstance(ssid, str) or not 1 <= len(ssid.encode()) <= 32:
        raise ValueError('Invalid Wi-Fi SSID')
    if not isinstance(password, str) or len(password.encode()) > 64:
        raise ValueError('Invalid Wi-Fi password')
    allowed = (18, 19, 21, 22, 23, 25, 26, 27, 32, 33)
    pins = (result['TRIG_PIN'], result['ECHO_PIN'])
    if any(type(pin) is not int or pin not in allowed for pin in pins) or pins[0] == pins[1]:
        raise ValueError('Invalid classic ESP32 GPIO mapping')
    capacity = result['OUTBOX_CAPACITY']
    if type(capacity) is not int or not 1 <= capacity <= 4096:
        raise ValueError('Invalid outbox capacity')
    path = result['OUTBOX_PATH']
    if (not isinstance(path, str) or not path.startswith('/') or len(path) < 2
            or '/' in path[1:] or '..' in path):
        raise ValueError('Use a dedicated top-level outbox directory')
    if not isinstance(result['CA_FILE'], str) or not result['CA_FILE']:
        raise ValueError('CA_FILE must identify the trusted certificate')
    host = result['NTP_HOST']
    if host is not None and (not isinstance(host, str) or not host or len(host) > 253
            or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-' for c in host)):
        raise ValueError('Invalid NTP host')
    return result


def start():
    import sys
    import time
    import network
    if sys.platform != 'esp32' or sys.implementation.version[:3] < (1, 29, 0):
        raise RuntimeError('Requires ESP32 MicroPython 1.29.0 or later')
    with open('config.secret.json') as stream:
        settings = validate_config(json.load(stream))
    transport = HTTPTransport(settings['TLM_API_URL'], settings['TLM_DEVICE_TOKEN'],
                              ca_file=settings['CA_FILE'],
                              allow_insecure_http=settings['ALLOW_INSECURE_HTTP'])
    queue = FileOutbox(settings['OUTBOX_PATH'], settings['TLM_DEVICE_ID'],
                       settings['OUTBOX_CAPACITY'])
    sensor = HCSR04(settings['TRIG_PIN'], settings['ECHO_PIN'])
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.config(reconnects=3)
    next_connect = time.ticks_ms()
    next_ntp = time.ticks_ms()

    async def ready():
        nonlocal next_connect, next_ntp
        now = time.ticks_ms()
        if not wlan.isconnected():
            if time.ticks_diff(now, next_connect) >= 0:
                next_connect = time.ticks_add(now, 15000)
                try:
                    wlan.disconnect()
                    wlan.connect(settings['WIFI_SSID'], settings['WIFI_PASSWORD'])
                except OSError:
                    print('wifi_retry')
            return False
        # TLS needs plausible UTC. NTP is NOT promoted to trusted measurement time.
        # MicroPython DNS and ntptime are blocking: see timing limitations in README.
        if transport.secure and time.gmtime()[0] < 2024:
            if time.ticks_diff(now, next_ntp) >= 0:
                next_ntp = time.ticks_add(now, 60000)
                if settings['NTP_HOST'] is not None:
                    import ntptime
                    ntptime.host = settings['NTP_HOST']
                    ntptime.timeout = 2
                    try:
                        ntptime.settime()
                    except OSError:
                        print('clock_unavailable: queued data retained')
            return time.gmtime()[0] >= 2024
        return True

    try:
        asyncio.run(run(queue, sensor, settings['TLM_DEVICE_ID'], transport, ready, time))
    finally:
        sensor.trigger.value(0)


if __name__ == '__main__':
    try:
        start()
    except KeyboardInterrupt:
        print('stopped: outbox retained')
    except Exception as error:
        # Do not print configuration, tokens, URLs containing credentials, or tracebacks.
        print('fatal:', type(error).__name__, '- inspect wiring/config/outbox; no auto-format')
