"""Reject unsafe device configuration before enabling GPIO or networking."""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / 'firmware' / 'esp32_micropython'


@pytest.fixture
def boot(monkeypatch):
    for name in ('tlm_core', 'hcsr04', 'tlm_http', 'tlm_runtime', 'main'):
        spec = importlib.util.spec_from_file_location('esp32_boot' if name == 'main' else name,
                                                      ROOT / (name + '.py'))
        module = importlib.util.module_from_spec(spec)
        if name != 'main':
            monkeypatch.setitem(sys.modules, name, module)
        spec.loader.exec_module(module)
    return module


def config():
    return {'TLM_DEVICE_ID': '11111111-1111-4111-8111-111111111111',
            'TLM_DEVICE_TOKEN': 'x' * 43, 'TLM_API_URL': 'https://api.example.com/v1/telemetry',
            'WIFI_SSID': 'test-fixture', 'WIFI_PASSWORD': 'test-only-password'}


def test_defaults_are_safe_and_ten_second_cadence_is_not_overridden(boot):
    result = boot.validate_config(config())
    assert result['ALLOW_INSECURE_HTTP'] is False
    assert result['TRIG_PIN'] == 26 and result['ECHO_PIN'] == 27
    assert result['OUTBOX_CAPACITY'] == 512
    assert result['CA_FILE'] == 'ca.pem'


def test_second_start_rejects_before_touching_hardware(boot, monkeypatch):
    monkeypatch.setattr(boot, 'runtime_active', lambda: True, raising=False)
    with pytest.raises(RuntimeError, match='already running'):
        boot.start()


@pytest.mark.parametrize('key,value', [('ALLOW_INSECURE_HTTP', 'false'),
    ('TLM_DATABASE_DSN', 'never-on-device'), ('TRIG_PIN', 6), ('ECHO_PIN', 26),
    ('TRIG_PIN', 26.0), ('OUTBOX_CAPACITY', 0), ('OUTBOX_CAPACITY', True),
    ('WIFI_SSID', ''), ('TLM_DEVICE_TOKEN', 'bad'), ('TLM_DEVICE_ID', 'bad'),
    ('OUTBOX_PATH', '/../../root'), ('SAMPLE_INTERVAL', 5)])
def test_unsafe_or_unknown_settings_are_rejected(boot, key, value):
    settings = config()
    settings[key] = value
    with pytest.raises(ValueError):
        boot.validate_config(settings)
