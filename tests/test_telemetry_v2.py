"""The v2 contract adds explicit, immutable session attribution."""
import json
from uuid import uuid4

import pytest

from tlm_device_data_platform.telemetry_v1 import InvalidTelemetry, TelemetryV1
from tlm_device_data_platform.telemetry_v2 import TelemetryV2, parse_message


def envelope(session=None):
    return {"schema_version": 2, "device_id": str(uuid4()), "message_id": str(uuid4()),
            "stream_id": str(uuid4()), "sequence_no": 1, "captured_at": None,
            "payload": {"test_sensor": 1.25}, "session_id": session}


@pytest.mark.parametrize('session', [None, str(uuid4())])
def test_roundtrip(session):
    message = TelemetryV2.parse(json.dumps(envelope(session)).encode())
    assert str(
        message.session_id) == session if session else message.session_id is None
    assert parse_message(message.to_bytes()) == message
    with pytest.raises(InvalidTelemetry):
        TelemetryV1.parse(message.to_bytes())


@pytest.mark.parametrize('session', [123, True, '', 'invalid'])
def test_invalid_session(session):
    with pytest.raises(InvalidTelemetry):
        TelemetryV2.parse(json.dumps(envelope(session)).encode())


def test_no_missing_extra_duplicate_or_coerced_fields():
    data = envelope()
    del data['session_id']
    with pytest.raises(InvalidTelemetry):
        TelemetryV2.parse(json.dumps(data).encode())
    data = envelope()
    data['schema_version'] = True
    with pytest.raises(InvalidTelemetry):
        TelemetryV2.parse(json.dumps(data).encode())
    with pytest.raises(InvalidTelemetry):
        TelemetryV2.parse(json.dumps(envelope()).replace(
            '"session_id": null', '"session_id": null, "session_id": null').encode())


def test_overflowing_float_is_rejected_as_protocol_error():
    body = json.dumps(envelope()).replace('1.25', '1e999').encode()
    with pytest.raises(InvalidTelemetry):
        TelemetryV2.parse(body)
