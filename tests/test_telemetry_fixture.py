import json

import pytest

from tlm_device_data_platform.simulation import ScriptedTransport
from tlm_device_data_platform.telemetry_fixture import (
    FIXTURE_SCHEMA_VERSION,
    MalformedTelemetryFixtureError,
    TelemetryFixtureEnvelope,
    UnsupportedFixtureSchemaVersionError,
    parse_fixture_telemetry,
    serialize_fixture_telemetry,
)


TEST_STREAM_ID = "test-stream-a"
TEST_RECORDED_AT = "2042-01-02T03:04:05Z"
TEST_ENVELOPES = tuple(
    TelemetryFixtureEnvelope(
        schema_version=FIXTURE_SCHEMA_VERSION,
        message_id=f"test-message-{sequence_no}",
        stream_id=TEST_STREAM_ID,
        sequence_no=sequence_no,
        recorded_at=TEST_RECORDED_AT,
        payload={"test_reading": sequence_no * 10},
    )
    for sequence_no in (1, 2, 3)
)


def test_normal_fixture_telemetry_is_delivered_in_configured_order() -> None:
    messages = tuple(serialize_fixture_telemetry(item) for item in TEST_ENVELOPES)
    transport = ScriptedTransport((True, True, True))

    results = tuple(transport.send(message) for message in messages)
    accepted = tuple(parse_fixture_telemetry(message) for message in transport.attempts)

    assert results == (True, True, True)
    assert accepted == TEST_ENVELOPES
    assert tuple(item.sequence_no for item in accepted) == (1, 2, 3)


def test_fixture_telemetry_serialization_is_deterministic() -> None:
    envelope = TEST_ENVELOPES[0]

    first_message = serialize_fixture_telemetry(envelope)
    second_message = serialize_fixture_telemetry(envelope)

    assert first_message == second_message
    assert parse_fixture_telemetry(first_message) == envelope


@pytest.mark.parametrize(
    "message",
    (
        b"not-json",
        b"[]",
        json.dumps(
            {
                "schema_version": FIXTURE_SCHEMA_VERSION,
                "message_id": "test-message-malformed",
            }
        ).encode("utf-8"),
        json.dumps(
            {
                "schema_version": FIXTURE_SCHEMA_VERSION,
                "message_id": "test-message-malformed",
                "stream_id": TEST_STREAM_ID,
                "sequence_no": "1",
                "recorded_at": TEST_RECORDED_AT,
                "payload": {"test_reading": 10},
            }
        ).encode("utf-8"),
    ),
)
def test_malformed_fixture_telemetry_is_rejected(message: bytes) -> None:
    with pytest.raises(MalformedTelemetryFixtureError, match="Fixture"):
        parse_fixture_telemetry(message)


def test_unsupported_fixture_schema_version_is_rejected_separately() -> None:
    document = json.loads(serialize_fixture_telemetry(TEST_ENVELOPES[0]))
    document["schema_version"] = 999

    with pytest.raises(
        UnsupportedFixtureSchemaVersionError,
        match="Unsupported fixture schema version: 999",
    ):
        parse_fixture_telemetry(json.dumps(document).encode("utf-8"))
