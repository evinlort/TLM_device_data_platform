import io
import json
from pathlib import Path
import sqlite3
from threading import Event, Thread
from types import SimpleNamespace
from uuid import uuid4

import pytest

from tlm_device_data_platform.edge_agent import (
    Delivery, FatalDelivery, HTTPSender, Outbox, OutboxFull, deliver_one, run_agent,
)
from tlm_device_data_platform.telemetry_v1 import TelemetryV1


def envelope(device_id, sequence=1):
    return TelemetryV1(device_id, uuid4(), uuid4(), sequence, None, {"test_sensor": 12.5})


def test_outbox_reopens_in_fifo_order_and_binds_device(tmp_path):
    device_id = uuid4()
    first, second = envelope(device_id), envelope(device_id, 2)
    path = tmp_path / "queue.sqlite"
    box = Outbox(path, device_id)
    box.enqueue(first.to_bytes())
    box.enqueue(second.to_bytes())
    reopened = Outbox(path, device_id)
    assert reopened.oldest() == (str(first.message_id), first.to_bytes())
    reopened.acknowledge(str(first.message_id))
    assert reopened.oldest() == (str(second.message_id), second.to_bytes())
    with pytest.raises(ValueError):
        Outbox(path, uuid4())


def test_capacity_never_evicts_pending_or_quarantined_messages(tmp_path):
    device_id = uuid4()
    box = Outbox(tmp_path / "queue.sqlite", device_id, max_records=1)
    first = envelope(device_id)
    box.enqueue(first.to_bytes())
    box.quarantine(str(first.message_id), "http_409")
    with pytest.raises(OutboxFull):
        box.enqueue(envelope(device_id, 2).to_bytes())
    with sqlite3.connect(box.path) as db:
        assert db.execute("SELECT body FROM messages").fetchone()[0] == first.to_bytes()


def test_retry_preserves_bytes_and_ack_deletes_only_that_message(tmp_path):
    device_id = uuid4()
    box = Outbox(tmp_path / "queue.sqlite", device_id)
    message = envelope(device_id)
    box.enqueue(message.to_bytes())
    attempts = []
    results = iter([Delivery("retry"), Delivery("ack")])

    def send(body):
        attempts.append(body)
        return next(results)

    sender = SimpleNamespace(send=send)
    assert deliver_one(box, sender).action == "retry"
    assert box.oldest() is not None
    assert deliver_one(box, sender).action == "ack"
    assert attempts == [message.to_bytes(), message.to_bytes()]
    assert box.counts() == {}


class Response(io.BytesIO):
    def __init__(self, status, body=b"{}", headers=None):
        super().__init__(body)
        self.status, self.headers = status, headers or {}


@pytest.mark.parametrize("status,action", [(409, "quarantine"), (422, "quarantine"),
    (503, "retry"), (429, "retry"), (408, "retry")])
def test_http_failure_classification(status, action):
    sender = HTTPSender("https://example.invalid/v1/telemetry", "a" * 43)
    sender._opener = SimpleNamespace(open=lambda *a, **k: Response(status))
    assert sender.send(envelope(uuid4()).to_bytes()).action == action


@pytest.mark.parametrize("status", [301, 302, 401, 403, 404])
def test_redirects_and_auth_errors_stop_without_ack(status):
    sender = HTTPSender("https://example.invalid/v1/telemetry", "a" * 43)
    sender._opener = SimpleNamespace(open=lambda *a, **k: Response(status))
    with pytest.raises(FatalDelivery):
        sender.send(envelope(uuid4()).to_bytes())


def test_receipt_must_identify_the_exact_message():
    sender = HTTPSender("https://example.invalid/v1/telemetry", "a" * 43)
    message = envelope(uuid4())
    receipt = {"status": "stored", "device_id": str(message.device_id),
               "message_id": str(uuid4()), "received_at": "2026-10-02T00:00:00+00:00"}
    sender._opener = SimpleNamespace(open=lambda *a, **k: Response(201, json.dumps(receipt).encode()))
    assert sender.send(message.to_bytes()).action == "retry"
    receipt["message_id"] = str(message.message_id)
    assert sender.send(message.to_bytes()).action == "ack"


def test_insecure_http_requires_explicit_opt_in():
    with pytest.raises(ValueError):
        HTTPSender("http://127.0.0.1:8000/v1/telemetry", "a" * 43)
    HTTPSender("http://127.0.0.1:8000/v1/telemetry", "a" * 43, allow_insecure_http=True)
    with pytest.raises(ValueError):
        HTTPSender("https://user:password@example.invalid/v1/telemetry", "a" * 43)


def test_collection_continues_while_sender_is_blocked(tmp_path):
    all_read, release = Event(), Event()
    calls, failures = [], []
    box = Outbox(tmp_path / "queue.sqlite", uuid4())

    def reader():
        calls.append(len(calls) + 1)
        if len(calls) == 3:
            all_read.set()
        return {"test_sensor": calls[-1]}

    def send(body):
        assert release.wait(2)
        return Delivery("ack")

    def agent():
        try:
            run_agent(box, SimpleNamespace(send=send), reader,
                      interval=0.001, count=3, drain_seconds=2)
        except Exception as error:
            failures.append(error)

    thread = Thread(target=agent, daemon=True)
    thread.start()
    try:
        assert all_read.wait(2), "Collection was blocked by transport"
    finally:
        release.set()
        thread.join(3)
    assert not thread.is_alive()
    assert failures == []
    assert calls == [1, 2, 3]
    assert box.counts() == {}
