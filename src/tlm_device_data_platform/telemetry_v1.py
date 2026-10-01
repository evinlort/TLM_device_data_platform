"""Laboratory wire contract v1; independent of hardware and storage providers."""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Mapping
from uuid import UUID

MAX_BODY_BYTES = 65536
MAX_SENSORS = 128
_FIELDS = frozenset({"schema_version", "device_id", "message_id", "stream_id",
                     "sequence_no", "captured_at", "payload"})
_SENSOR_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z")
_TIMESTAMP = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})\Z"
)


class InvalidTelemetry(ValueError):
    """The message does not satisfy the laboratory wire contract."""


class AuthenticationFailed(Exception):
    """The device token is unknown, expired, or revoked."""


class DeviceMismatch(Exception):
    """The token is not authorized for the message's device."""


class MessageConflict(Exception):
    """A message ID or stream position was reused for different data."""


class StorageUnavailable(Exception):
    """Persistence failed; the sender must retain its message."""


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidTelemetry("Duplicate JSON keys are not allowed")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise InvalidTelemetry("Non-finite numbers are not allowed")


@dataclass(frozen=True)
class TelemetryV1:
    device_id: UUID
    message_id: UUID
    stream_id: UUID
    sequence_no: int
    captured_at: datetime | None
    payload: Mapping[str, int | float]

    @classmethod
    def parse(cls, body: bytes) -> TelemetryV1:
        if not isinstance(body, bytes) or not 0 < len(body) <= MAX_BODY_BYTES:
            raise InvalidTelemetry("Message size is outside the permitted range")
        try:
            data = json.loads(body.decode("utf-8"), object_pairs_hook=_unique_object,
                              parse_constant=_reject_constant)
            if not isinstance(data, dict) or set(data) != _FIELDS:
                raise InvalidTelemetry("Unexpected or missing envelope fields")
            if type(data["schema_version"]) is not int or data["schema_version"] != 1:
                raise InvalidTelemetry("Unsupported schema_version")
            ids = []
            for key in ("device_id", "message_id", "stream_id"):
                if not isinstance(data[key], str):
                    raise InvalidTelemetry("Identifiers must be UUID strings")
                ids.append(UUID(data[key]))
            seq = data["sequence_no"]
            if type(seq) is not int or not 1 <= seq <= 9223372036854775807:
                raise InvalidTelemetry("sequence_no must be a positive signed bigint")
            captured = data["captured_at"]
            if captured is not None:
                if not isinstance(captured, str) or not _TIMESTAMP.fullmatch(captured):
                    raise InvalidTelemetry("captured_at must be RFC3339 or null")
                captured = datetime.fromisoformat(captured.replace("Z", "+00:00"))
                captured = captured.astimezone(timezone.utc)
            payload = data["payload"]
            if not isinstance(payload, dict) or not 1 <= len(payload) <= MAX_SENSORS:
                raise InvalidTelemetry("payload must contain 1 to 128 sensor readings")
            for key, value in payload.items():
                if not _SENSOR_NAME.fullmatch(key):
                    raise InvalidTelemetry("Invalid sensor name")
                if type(value) not in (int, float):
                    raise InvalidTelemetry("Sensor readings must be numbers, not booleans")
                if isinstance(value, float) and not math.isfinite(value):
                    raise InvalidTelemetry("Sensor readings must be finite")
            return cls(*ids, seq, captured, MappingProxyType(payload))
        except (ValueError, TypeError, OverflowError, RecursionError) as error:
            if isinstance(error, InvalidTelemetry):
                raise
            raise InvalidTelemetry("Malformed telemetry envelope") from error

    def to_bytes(self) -> bytes:
        data = {
            "schema_version": 1,
            "device_id": str(self.device_id), "message_id": str(self.message_id),
            "stream_id": str(self.stream_id), "sequence_no": self.sequence_no,
            "captured_at": (self.captured_at.isoformat().replace("+00:00", "Z")
                            if self.captured_at is not None else None),
            "payload": dict(self.payload),
        }
        body = json.dumps(data, allow_nan=False, sort_keys=True,
                          separators=(",", ":")).encode("utf-8")
        self.parse(body)
        return body


@dataclass(frozen=True)
class IngestReceipt:
    device_id: UUID
    message_id: UUID
    received_at: datetime
    duplicate: bool
