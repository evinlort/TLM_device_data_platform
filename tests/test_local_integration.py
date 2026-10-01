from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from threading import Thread
from urllib.error import URLError
from urllib.request import Request, urlopen
from wsgiref.simple_server import WSGIRequestHandler, make_server

from tlm_device_data_platform.local_integration import (
    OpaqueTelemetryAPI,
    TemporaryDirectoryStorage,
)
from tlm_device_data_platform.simulation import (
    TemporaryFileQueue,
    flush_test_queue,
)
from tlm_device_data_platform.telemetry_fixture import (
    FIXTURE_SCHEMA_VERSION,
    TelemetryFixtureEnvelope,
    parse_fixture_telemetry,
    serialize_fixture_telemetry,
)


TEST_INGEST_PATH = "/test-fixture-telemetry"
TEST_ENVELOPE = TelemetryFixtureEnvelope(
    schema_version=FIXTURE_SCHEMA_VERSION,
    message_id="test-step-7-message-1",
    stream_id="test-step-7-stream",
    sequence_no=1,
    recorded_at="2042-01-02T03:04:05Z",
    payload={"test_reading": 10},
)


class _QuietWSGIRequestHandler(WSGIRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        """Keep the deterministic test output free of local server logs."""


class _LoopbackHTTPTransport:
    """Map one configured local HTTP outcome to the test Transport contract."""

    def __init__(self, test_url: str) -> None:
        self._url = test_url

    def send(self, message: bytes) -> bool:
        request = Request(self._url, data=message, method="POST")
        try:
            with urlopen(request, timeout=2) as response:
                return response.status == 204
        except URLError:
            return False


@contextmanager
def _serve_local_api(storage: TemporaryDirectoryStorage) -> Iterator[str]:
    application = OpaqueTelemetryAPI(
        storage,
        test_ingest_path=TEST_INGEST_PATH,
    )
    server = make_server(
        "127.0.0.1",
        0,
        application,
        handler_class=_QuietWSGIRequestHandler,
    )
    server_thread = Thread(
        target=server.serve_forever,
        kwargs={"poll_interval": 0.01},
        daemon=True,
    )
    server_thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}{TEST_INGEST_PATH}"
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=2)


def _enqueue(queue_path: Path, message: bytes) -> None:
    TemporaryFileQueue(queue_path).enqueue(message)


def test_fixture_crosses_real_local_http_and_storage_boundaries(tmp_path) -> None:
    queue_path = tmp_path / "test-delivery-queue.json"
    storage_path = tmp_path / "test-storage"
    message = serialize_fixture_telemetry(TEST_ENVELOPE)
    _enqueue(queue_path, message)

    with _serve_local_api(TemporaryDirectoryStorage(storage_path)) as test_url:
        delivered = flush_test_queue(
            TemporaryFileQueue(queue_path),
            _LoopbackHTTPTransport(test_url),
        )

    stored_messages = TemporaryDirectoryStorage(storage_path).read_all()
    assert delivered == (message,)
    assert len(TemporaryFileQueue(queue_path)) == 0
    assert stored_messages == (message,)
    assert parse_fixture_telemetry(stored_messages[0]) == TEST_ENVELOPE


def test_local_api_and_storage_keep_non_fixture_bytes_opaque(tmp_path) -> None:
    storage_path = tmp_path / "test-storage"
    opaque_message = b"\x00test-not-a-telemetry-fixture\xff"

    with _serve_local_api(TemporaryDirectoryStorage(storage_path)) as test_url:
        assert _LoopbackHTTPTransport(test_url).send(opaque_message) is True

    assert TemporaryDirectoryStorage(storage_path).read_all() == (opaque_message,)
