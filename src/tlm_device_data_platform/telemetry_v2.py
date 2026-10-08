"""Session-aware wire contract; v1 remains strict and backwards compatible."""
from dataclasses import dataclass
import json
from uuid import UUID

from .telemetry_v1 import (
    MAX_BODY_BYTES, InvalidTelemetry, TelemetryV1, _unique_object, _reject_constant,
)


@dataclass(frozen=True)
class TelemetryV2(TelemetryV1):
    session_id: UUID | None

    @classmethod
    def parse(cls, body: bytes):
        data = _decode(body)
        if not isinstance(data, dict) or 'session_id' not in data:
            raise InvalidTelemetry('session_id is required in v2')
        if type(data.get('schema_version')) is not int or data['schema_version'] != 2:
            raise InvalidTelemetry('Unsupported schema_version')
        session = data.pop('session_id')
        try:
            if session is not None:
                if not isinstance(session, str):
                    raise ValueError
                session = UUID(session)
        except ValueError:
            raise InvalidTelemetry('session_id must be UUID or null') from None
        data['schema_version'] = 1
        try:
            base = TelemetryV1.parse(json.dumps(
                data, allow_nan=False).encode())
        except (ValueError, TypeError, RecursionError):
            raise InvalidTelemetry('Malformed telemetry envelope') from None
        return cls(base.device_id, base.message_id, base.stream_id, base.sequence_no,
                   base.captured_at, base.payload, session)

    def to_bytes(self):
        base = TelemetryV1(self.device_id, self.message_id, self.stream_id,
                           self.sequence_no, self.captured_at, self.payload)
        data = json.loads(base.to_bytes())
        data.update(schema_version=2, session_id=str(
            self.session_id) if self.session_id else None)
        body = json.dumps(data, allow_nan=False, sort_keys=True,
                          separators=(',', ':')).encode()
        self.parse(body)
        return body


def _decode(body):
    if not isinstance(body, bytes) or not 0 < len(body) <= MAX_BODY_BYTES:
        raise InvalidTelemetry('Invalid message size')
    try:
        return json.loads(body.decode(), object_pairs_hook=_unique_object,
                          parse_constant=_reject_constant)
    except (ValueError, UnicodeError, RecursionError):
        raise InvalidTelemetry('Malformed telemetry envelope') from None


def parse_message(body):
    data = _decode(body)
    version = data.get('schema_version') if isinstance(data, dict) else None
    if type(version) is not int or version not in (1, 2):
        raise InvalidTelemetry('Unsupported schema_version')
    return (TelemetryV1 if version == 1 else TelemetryV2).parse(body)
