"""Test-only telemetry contract for deterministic CI scenarios.

The field names and schema version in this module are test fixtures. They do
not define the product telemetry contract or production acceptance policy.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any


FIXTURE_SCHEMA_VERSION = 1
_FIXTURE_FIELDS = frozenset(
    {
        "schema_version",
        "message_id",
        "stream_id",
        "sequence_no",
        "recorded_at",
        "payload",
    }
)


class TelemetryFixtureError(ValueError):
    """Base error for the test-only telemetry contract."""


class MalformedTelemetryFixtureError(TelemetryFixtureError):
    """Signal that bytes do not contain a valid fixture envelope."""


class UnsupportedFixtureSchemaVersionError(TelemetryFixtureError):
    """Signal that a well-formed fixture uses an unsupported test version."""


@dataclass(frozen=True)
class TelemetryFixtureEnvelope:
    """Test-only envelope; every field remains unconfirmed product behavior."""

    schema_version: int
    message_id: str
    stream_id: str
    sequence_no: int
    recorded_at: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class ObservedTelemetryFixture:
    """One test observation kept separately from device-recorded fixture time."""

    observation_no: int
    observed_at: datetime
    envelope: TelemetryFixtureEnvelope


class TelemetryFixtureProjection:
    """Keep test history and project state for one explicitly active fixture stream.

    Stream activation is controlled by the test harness. Device-provided
    ``recorded_at`` values never activate a stream or decide which observation
    becomes current. This class is deterministic fixture orchestration, not a
    production persistence, ordering, reboot, trust, or authorization policy.
    """

    def __init__(self, test_active_stream_id: str) -> None:
        self._active_stream_id = test_active_stream_id
        self._history: list[ObservedTelemetryFixture] = []
        self._current_state: TelemetryFixtureEnvelope | None = None

    @property
    def history(self) -> tuple[ObservedTelemetryFixture, ...]:
        """Return every fixture observation in deterministic arrival order."""
        return tuple(self._history)

    @property
    def current_state(self) -> TelemetryFixtureEnvelope | None:
        """Return the highest-sequence observation in the active test stream."""
        return self._current_state

    @property
    def active_stream_id(self) -> str:
        """Return the stream explicitly selected by the test harness."""
        return self._active_stream_id

    def activate_test_stream(self, test_stream_id: str) -> None:
        """Select a fixture stream and permit its sequence to restart.

        Calling this method represents an explicit test event. It must not be
        inferred from an untrusted fixture timestamp or treated as device
        authorization.
        """
        self._active_stream_id = test_stream_id
        self._current_state = None

    def observe(
        self,
        message: bytes,
        *,
        observed_at: datetime,
    ) -> ObservedTelemetryFixture:
        """Record one fixture arrival and update only its active stream state."""
        envelope = parse_fixture_telemetry(message)
        observation = ObservedTelemetryFixture(
            observation_no=len(self._history) + 1,
            observed_at=observed_at,
            envelope=envelope,
        )
        self._history.append(observation)

        if envelope.stream_id != self._active_stream_id:
            return observation

        if (
            self._current_state is None
            or envelope.sequence_no > self._current_state.sequence_no
        ):
            self._current_state = envelope

        return observation


def serialize_fixture_telemetry(envelope: TelemetryFixtureEnvelope) -> bytes:
    """Validate and deterministically serialize one test fixture envelope."""
    document = {
        "schema_version": envelope.schema_version,
        "message_id": envelope.message_id,
        "stream_id": envelope.stream_id,
        "sequence_no": envelope.sequence_no,
        "recorded_at": envelope.recorded_at,
        "payload": envelope.payload,
    }
    _validate_fixture_document(document)

    try:
        serialized = json.dumps(
            document,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as error:
        raise MalformedTelemetryFixtureError(
            "Fixture envelope contains a value that JSON cannot represent"
        ) from error
    return serialized.encode("utf-8")


def parse_fixture_telemetry(message: bytes) -> TelemetryFixtureEnvelope:
    """Parse bytes and return a validated test fixture envelope."""
    if not isinstance(message, bytes):
        raise MalformedTelemetryFixtureError("Fixture message must be bytes")

    try:
        document = json.loads(
            message.decode("utf-8"),
            parse_constant=_reject_non_finite_number,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise MalformedTelemetryFixtureError(
            "Fixture message must be finite-value UTF-8 JSON"
        ) from error

    return _validate_fixture_document(document)


def _validate_fixture_document(document: object) -> TelemetryFixtureEnvelope:
    if not isinstance(document, dict):
        raise MalformedTelemetryFixtureError("Fixture envelope must be a JSON object")

    if set(document) != _FIXTURE_FIELDS:
        raise MalformedTelemetryFixtureError(
            "Fixture envelope must contain exactly the configured test fields"
        )

    schema_version = document["schema_version"]
    if type(schema_version) is not int:
        raise MalformedTelemetryFixtureError(
            "Fixture schema_version must be an integer"
        )

    for field in ("message_id", "stream_id", "recorded_at"):
        if not isinstance(document[field], str):
            raise MalformedTelemetryFixtureError(
                f"Fixture {field} must be a string"
            )

    sequence_no = document["sequence_no"]
    if type(sequence_no) is not int:
        raise MalformedTelemetryFixtureError(
            "Fixture sequence_no must be an integer"
        )

    payload = document["payload"]
    if not isinstance(payload, dict):
        raise MalformedTelemetryFixtureError("Fixture payload must be a JSON object")

    if schema_version != FIXTURE_SCHEMA_VERSION:
        raise UnsupportedFixtureSchemaVersionError(
            f"Unsupported fixture schema version: {schema_version}"
        )

    return TelemetryFixtureEnvelope(
        schema_version=schema_version,
        message_id=document["message_id"],
        stream_id=document["stream_id"],
        sequence_no=sequence_no,
        recorded_at=document["recorded_at"],
        payload=dict(payload),
    )


def _reject_non_finite_number(value: str) -> None:
    raise ValueError(f"Non-finite JSON number is not allowed: {value}")
