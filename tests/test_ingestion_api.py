import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tlm_device_data_platform.ingestion import create_app
from tlm_device_data_platform.telemetry_v1 import (
    AuthenticationFailed, DeviceMismatch, IngestReceipt, MessageConflict, StorageUnavailable,
)

TEST_TOKEN = "a" * 43


def body():
    return {"schema_version": 1, "device_id": str(uuid4()), "message_id": str(uuid4()),
            "stream_id": str(uuid4()), "sequence_no": 1, "captured_at": None,
            "payload": {"test_sensor": 12.5}}


class TestRepository:
    __test__ = False

    def __init__(self, error=None, duplicate=False):
        self.error, self.duplicate, self.calls = error, duplicate, []

    def accept(self, token, message):
        self.calls.append((token, message))
        if self.error:
            raise self.error
        return IngestReceipt(message.device_id, message.message_id,
                             datetime(2026, 10, 2, tzinfo=timezone.utc), self.duplicate)


@pytest.mark.parametrize("duplicate,expected", [(False, 201), (True, 200)])
def test_successful_receipt(duplicate, expected):
    repository = TestRepository(duplicate=duplicate)
    with TestClient(create_app(repository)) as client:
        data = body()
        response = client.post("/v1/telemetry", json=data,
                               headers={"Authorization": f"Bearer {TEST_TOKEN}"})
        assert response.status_code == expected
        assert response.json()["message_id"] == data["message_id"]
        assert response.json()["status"] == ("duplicate" if duplicate else "stored")
        assert len(repository.calls) == 1


@pytest.mark.parametrize("error,status", [(AuthenticationFailed(), 401),
    (DeviceMismatch(), 403), (MessageConflict(), 409), (StorageUnavailable(), 503)])
def test_repository_failure_never_acknowledges(error, status):
    with TestClient(create_app(TestRepository(error))) as client:
        response = client.post("/v1/telemetry", json=body(),
                               headers={"Authorization": f"Bearer {TEST_TOKEN}"})
        assert response.status_code == status
        assert "received_at" not in response.json()


def test_missing_auth_bad_content_and_oversize_never_reach_storage():
    repository = TestRepository()
    with TestClient(create_app(repository)) as client:
        assert client.post("/v1/telemetry", json=body()).status_code == 401
        headers = {"Authorization": f"Bearer {TEST_TOKEN}"}
        assert client.post("/v1/telemetry", content=b"{}", headers=headers).status_code == 415
        headers["Content-Type"] = "application/json"
        assert client.post("/v1/telemetry", content=b"x" * 65537,
                           headers=headers).status_code == 413
        assert client.post("/v1/telemetry", content=b"{}", headers=headers).status_code == 422
        assert repository.calls == []


def test_actual_chunked_body_size_is_checked_without_content_length():
    repository = TestRepository()
    with TestClient(create_app(repository)) as client:
        response = client.post("/v1/telemetry", content=iter([b"x" * 32768] * 3),
            headers={"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"})
        assert response.status_code == 413
        assert repository.calls == []
