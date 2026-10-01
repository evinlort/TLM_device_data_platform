"""Provider-independent API/storage boundary and local test implementations.

The HTTP path, response status, and directory layout used here are local test
configuration. They do not define the production telemetry, acknowledgement,
storage, authentication, or authorization contracts.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any, Protocol


StartResponse = Callable[[str, list[tuple[str, str]]], Any]


class StorageAdapter(Protocol):
    """Store one opaque message without prescribing a storage provider."""

    def store(self, message: bytes) -> None:
        """Persist the message or raise an implementation-specific error."""


class TemporaryDirectoryStorage:
    """Persist opaque messages as ordered files in a temporary test directory.

    This adapter exists to exercise a real local storage boundary in CI. Its
    file names and durability properties are not a production storage design.
    """

    _RECORD_PREFIX = "test-message-"
    _RECORD_SUFFIX = ".bin"

    def __init__(self, test_directory: Path) -> None:
        self._directory = test_directory

    def store(self, message: bytes) -> None:
        if not isinstance(message, bytes):
            raise TypeError("Storage message must be bytes")

        self._directory.mkdir(parents=True, exist_ok=True)
        record_number = self._next_record_number()
        record_path = self._record_path(record_number)
        temporary_path = record_path.with_suffix(f"{record_path.suffix}.tmp")
        temporary_path.write_bytes(message)
        temporary_path.replace(record_path)

    def read_all(self) -> tuple[bytes, ...]:
        """Read stored test messages in deterministic arrival order."""
        return tuple(path.read_bytes() for path in self._record_paths())

    def _next_record_number(self) -> int:
        paths = self._record_paths()
        if not paths:
            return 1
        return self._record_number(paths[-1]) + 1

    def _record_paths(self) -> tuple[Path, ...]:
        if not self._directory.exists():
            return ()
        paths = tuple(
            path
            for path in self._directory.iterdir()
            if self._is_record_path(path)
        )
        return tuple(sorted(paths, key=self._record_number))

    def _record_path(self, record_number: int) -> Path:
        return self._directory / (
            f"{self._RECORD_PREFIX}{record_number:08d}{self._RECORD_SUFFIX}"
        )

    def _is_record_path(self, path: Path) -> bool:
        try:
            self._record_number(path)
        except ValueError:
            return False
        return path.is_file()

    def _record_number(self, path: Path) -> int:
        name = path.name
        if not name.startswith(self._RECORD_PREFIX) or not name.endswith(
            self._RECORD_SUFFIX
        ):
            raise ValueError("Not a local test storage record")
        number = name[len(self._RECORD_PREFIX) : -len(self._RECORD_SUFFIX)]
        if len(number) != 8 or not number.isascii() or not number.isdigit():
            raise ValueError("Not a local test storage record")
        return int(number)


class OpaqueTelemetryAPI:
    """Pass an HTTP request body to a provider-independent storage adapter.

    The configured path and the 204 response are test integration choices.
    The application deliberately does not parse fixture or product fields.
    """

    def __init__(self, storage: StorageAdapter, *, test_ingest_path: str) -> None:
        if not test_ingest_path.startswith("/"):
            raise ValueError("Test ingest path must start with '/'")
        self._storage = storage
        self._ingest_path = test_ingest_path

    def __call__(
        self,
        environ: dict[str, Any],
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        if (
            environ.get("REQUEST_METHOD") != "POST"
            or environ.get("PATH_INFO") != self._ingest_path
        ):
            return self._empty_response(start_response, "404 Not Found")

        content_length = self._content_length(environ.get("CONTENT_LENGTH"))
        if content_length is None:
            return self._empty_response(start_response, "400 Bad Request")

        message = environ["wsgi.input"].read(content_length)
        if len(message) != content_length:
            return self._empty_response(start_response, "400 Bad Request")

        self._storage.store(message)
        return self._empty_response(start_response, "204 No Content")

    @staticmethod
    def _content_length(raw_content_length: object) -> int | None:
        if not isinstance(raw_content_length, str):
            return None
        try:
            content_length = int(raw_content_length)
        except ValueError:
            return None
        return content_length if content_length >= 0 else None

    @staticmethod
    def _empty_response(
        start_response: StartResponse,
        status: str,
    ) -> tuple[bytes, ...]:
        start_response(status, [("Content-Length", "0")])
        return ()
