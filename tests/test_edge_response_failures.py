import io
from http.client import IncompleteRead
from types import SimpleNamespace
from uuid import uuid4

from tlm_device_data_platform.edge_agent import HTTPSender
from tlm_device_data_platform.telemetry_v1 import TelemetryV1


def test_interrupted_http_response_preserves_message_for_retry():
    sender = HTTPSender("https://example.invalid/v1/telemetry", "a" * 43)

    class InterruptedResponse(io.BytesIO):
        status = 201
        headers = {}

        def read(self, size=-1):
            raise IncompleteRead(b"partial", 100)

    sender._opener = SimpleNamespace(open=lambda *a, **k: InterruptedResponse())
    message = TelemetryV1(uuid4(), uuid4(), uuid4(), 1, None, {"test_sensor": 12.5})
    assert sender.send(message.to_bytes()).action == "retry"
