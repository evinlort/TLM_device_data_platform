"""Provider-independent boundaries and deterministic test implementations."""

from __future__ import annotations

import base64
import json
from collections import deque
from collections.abc import Iterable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Generic, Protocol, TypeVar


ReadingT_co = TypeVar("ReadingT_co", covariant=True)


class Sensor(Protocol[ReadingT_co]):
    """Produce one reading without prescribing its product schema."""

    def read(self) -> ReadingT_co:
        """Return the next reading."""


class Clock(Protocol):
    """Provide time without coupling consumers to the wall clock."""

    def now(self) -> datetime:
        """Return the current controlled time."""


class Transport(Protocol):
    """Attempt delivery of an opaque serialized message."""

    def send(self, message: bytes) -> bool:
        """Return whether the delivery attempt succeeded."""


class DurableQueue(Protocol):
    """Persist opaque serialized messages in first-in, first-out order."""

    def enqueue(self, message: bytes) -> None:
        """Append a message to the queue."""

    def peek(self) -> bytes | None:
        """Return the oldest message without removing it."""

    def dequeue(self) -> bytes | None:
        """Remove and return the oldest message."""

    def __len__(self) -> int:
        """Return the number of queued messages."""


def flush_test_queue(
    test_queue: DurableQueue,
    test_transport: Transport,
) -> tuple[bytes, ...]:
    """Attempt queued test messages in FIFO order until delivery is unavailable.

    This is deterministic test orchestration, not a production retry or
    acknowledgement policy. A configured successful transport result removes
    the matching message only within the test scenario. A failed result stops
    the explicit flush and leaves that message queued.
    """
    successful_attempts: list[bytes] = []

    while (message := test_queue.peek()) is not None:
        if not test_transport.send(message):
            break

        dequeued = test_queue.dequeue()
        if dequeued != message:
            raise RuntimeError("Test queue changed during deterministic flush")
        successful_attempts.append(message)

    return tuple(successful_attempts)


class FixtureExhaustedError(RuntimeError):
    """Signal that a deterministic test fixture has no configured value left."""


class SequenceSensor(Generic[ReadingT_co]):
    """Return explicitly configured test readings in order."""

    def __init__(self, test_readings: Iterable[ReadingT_co]) -> None:
        self._readings = deque(test_readings)

    def read(self) -> ReadingT_co:
        if not self._readings:
            raise FixtureExhaustedError("No configured test reading remains")
        return self._readings.popleft()


class ManualClock:
    """Expose time controlled entirely by test code."""

    def __init__(self, test_start: datetime) -> None:
        self._current = test_start

    def now(self) -> datetime:
        return self._current

    def advance(self, test_delta: timedelta) -> None:
        self._current += test_delta


class ScriptedTransport:
    """Return explicitly configured test delivery results in order."""

    def __init__(self, test_results: Iterable[bool]) -> None:
        self._results = deque(test_results)
        self._attempts: list[bytes] = []

    @property
    def attempts(self) -> tuple[bytes, ...]:
        """Return an immutable record of attempted test deliveries."""
        return tuple(self._attempts)

    def send(self, message: bytes) -> bool:
        if not self._results:
            raise FixtureExhaustedError("No configured test delivery result remains")
        self._attempts.append(message)
        return self._results.popleft()


class TemporaryFileQueue:
    """Persist a test queue in one temporary JSON file."""

    def __init__(self, test_path: Path) -> None:
        self._path = test_path

    def enqueue(self, message: bytes) -> None:
        messages = self._load()
        messages.append(message)
        self._store(messages)

    def peek(self) -> bytes | None:
        messages = self._load()
        return messages[0] if messages else None

    def dequeue(self) -> bytes | None:
        messages = self._load()
        if not messages:
            return None
        message = messages.pop(0)
        self._store(messages)
        return message

    def __len__(self) -> int:
        return len(self._load())

    def _load(self) -> list[bytes]:
        if not self._path.exists():
            return []
        encoded_messages = json.loads(self._path.read_text(encoding="utf-8"))
        return [base64.b64decode(message) for message in encoded_messages]

    def _store(self, messages: list[bytes]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        encoded_messages = [
            base64.b64encode(message).decode("ascii") for message in messages
        ]
        temporary_path = self._path.with_suffix(f"{self._path.suffix}.tmp")
        temporary_path.write_text(json.dumps(encoded_messages), encoding="utf-8")
        temporary_path.replace(self._path)
