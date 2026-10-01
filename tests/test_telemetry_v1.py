import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from tlm_device_data_platform.telemetry_v1 import InvalidTelemetry, TelemetryV1


def document():
    return {"schema_version": 1, "device_id": str(uuid4()), "message_id": str(uuid4()),
            "stream_id": str(uuid4()), "sequence_no": 1, "captured_at": None,
            "payload": {"test_sensor": 12.5}}


def test_wire_roundtrip():
    data = document()
    data["captured_at"] = "2026-10-02T10:00:00+03:00"
    envelope = TelemetryV1.parse(json.dumps(data).encode())
    assert envelope.captured_at == datetime(2026, 10, 2, 7, tzinfo=timezone.utc)
    assert TelemetryV1.parse(envelope.to_bytes()) == envelope
    with pytest.raises(TypeError):
        envelope.payload["test_sensor"] = 0


@pytest.mark.parametrize("field,value", [
    ("schema_version", True), ("schema_version", 2), ("device_id", 123),
    ("message_id", "bad-uuid"), ("sequence_no", True), ("sequence_no", 0),
    ("sequence_no", 2**63), ("captured_at", "2026-10-02"),
    ("captured_at", "2026-10-02T10:00:00"),
    ("payload", {}), ("payload", {"test_sensor": True}),
    ("payload", {"test_sensor": float("inf")}), ("payload", {"bad name": 1}),
    ("payload", {f"sensor_{i}": 1 for i in range(129)}),
])
def test_invalid_values(field, value):
    data = document()
    data[field] = value
    with pytest.raises(InvalidTelemetry):
        TelemetryV1.parse(json.dumps(data).encode())


@pytest.mark.parametrize("body", [b"", b"[]", b"\xff", b"{" * 2000, b"x" * 65537])
def test_malformed_bytes(body):
    with pytest.raises(InvalidTelemetry):
        TelemetryV1.parse(body)


def test_unknown_fields_and_duplicate_keys():
    data = document()
    data["received_at"] = "2026-10-02T00:00:00Z"
    with pytest.raises(InvalidTelemetry):
        TelemetryV1.parse(json.dumps(data).encode())
    del data["received_at"]
    body = json.dumps(data).replace('"test_sensor": 12.5',
                                    '"test_sensor": 12.5, "test_sensor": 13')
    with pytest.raises(InvalidTelemetry):
        TelemetryV1.parse(body.encode())


def test_overflowing_float_is_rejected():
    body = json.dumps(document()).replace("12.5", "1e999")
    with pytest.raises(InvalidTelemetry):
        TelemetryV1.parse(body.encode())
