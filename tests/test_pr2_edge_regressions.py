"""Regression coverage for PR #2; transport fixtures never contact a remote API."""
import io
from http.client import IncompleteRead
import sqlite3
import ssl
from threading import Event, Thread
from types import SimpleNamespace
from urllib.error import URLError
from uuid import uuid4

import pytest

from tlm_device_data_platform.edge_agent import (
    Delivery, FatalDelivery, HTTPSender, Outbox, OutboxFull, deliver_one, run_agent,
)
from tlm_device_data_platform.telemetry_v1 import TelemetryV1


def packet(device_id):
    return TelemetryV1(device_id, uuid4(), uuid4(), 1, None, {"test_sensor": 12.5})


@pytest.mark.parametrize("wrapped", [False, True], ids=["direct", "urlerror"])
@pytest.mark.parametrize("phase", ["open", "read"])
def test_certificate_failure_is_fatal_and_preserves_exact_packet(tmp_path, wrapped, phase):
    box = Outbox(tmp_path / "queue.sqlite", uuid4())
    message = packet(box.device_id)
    box.enqueue(message.to_bytes())
    certificate_error = ssl.SSLCertVerificationError(1, "test certificate rejected")
    error = URLError(certificate_error) if wrapped else certificate_error

    class BrokenResponse(io.BytesIO):
        status = 201
        headers = {}

        def read(self, size=-1):
            raise error

    def open_request(*args, **kwargs):
        if phase == "open":
            raise error
        return BrokenResponse()

    sender = HTTPSender("https://example.invalid/v1/telemetry", "a" * 43)
    sender._opener = SimpleNamespace(open=open_request)
    with pytest.raises(FatalDelivery, match="TLS certificate verification") as caught:
        deliver_one(box, sender)
    assert caught.value.__cause__ is error
    assert box.counts() == {"pending": 1}
    assert box.oldest() == (str(message.message_id), message.to_bytes())


@pytest.mark.parametrize("error", [
    TimeoutError("test timeout"),
    ConnectionResetError("test reset"),
    URLError(TimeoutError("test timeout")),
    URLError("test network unavailable"),
    IncompleteRead(b"partial", 100),
    ssl.SSLEOFError(8, "test abrupt TLS close"),
    URLError(ssl.SSLEOFError(8, "test abrupt TLS close")),
])
def test_transient_transport_failure_still_retries(tmp_path, error):
    box = Outbox(tmp_path / "queue.sqlite", uuid4())
    message = packet(box.device_id)
    box.enqueue(message.to_bytes())

    def open_request(*args, **kwargs):
        raise error

    sender = HTTPSender("https://example.invalid/v1/telemetry", "a" * 43)
    sender._opener = SimpleNamespace(open=open_request)
    assert deliver_one(box, sender) == Delivery("retry", "network_error")
    assert box.oldest() == (str(message.message_id), message.to_bytes())


@pytest.mark.parametrize("records,limit,quarantined", [(1, 1, 0), (3, 2, 0), (2, 2, 1)])
def test_full_restart_waits_for_ack_before_sampling(tmp_path, records, limit, quarantined):
    path, device_id = tmp_path / "queue.sqlite", uuid4()
    original = Outbox(path, device_id, max_records=records)
    messages = [packet(device_id) for _ in range(records)]
    for index, message in enumerate(messages):
        original.enqueue(message.to_bytes())
        if index < quarantined:
            original.quarantine(str(message.message_id), "http_409")

    sender_started, phase_reached, release, sampled = Event(), Event(), Event(), Event()
    attempts, failures, readings = [], [], []

    class ObservedOutbox(Outbox):
        def counts(self):
            counts = super().counts()
            if sum(counts.values()) >= self.max_records:
                phase_reached.set()
            return counts

    box = ObservedOutbox(path, device_id, max_records=limit)

    def reader():
        sampled.set()
        phase_reached.set()
        assert sender_started.wait(3)
        readings.append(sum(box.counts().values()))
        return {"test_sensor": 42}

    def send(body):
        sender_started.set()
        assert release.wait(3), "Test did not release the controlled transport"
        attempts.append(body)
        return Delivery("ack")

    def agent():
        try:
            run_agent(box, SimpleNamespace(send=send), reader, count=1,
                      interval=0.001, drain_seconds=2)
        except BaseException as error:
            failures.append(error)

    thread = Thread(target=agent, daemon=True)
    thread.start()
    try:
        assert sender_started.wait(3)
        assert phase_reached.wait(3)
        sampled_before_release = sampled.is_set()
    finally:
        release.set()
        thread.join(4)
    assert not thread.is_alive()
    assert not sampled_before_release, "Reader ran while the durable queue was still full"
    assert failures == []
    assert len(readings) == 1 and readings[0] < limit
    expected_pending = [m.to_bytes() for m in messages[quarantined:]]
    assert attempts[:-1] == expected_pending
    new_message = TelemetryV1.parse(attempts[-1])
    assert new_message.sequence_no == 1
    assert new_message.stream_id not in {m.stream_id for m in messages}
    assert new_message.payload == {"test_sensor": 42}
    with sqlite3.connect(path) as db:
        retained = db.execute("SELECT body, state FROM messages ORDER BY id").fetchall()
    assert retained == [(m.to_bytes(), "quarantined") for m in messages[:quarantined]]


@pytest.mark.parametrize("already_quarantined", [True, False])
def test_full_quarantine_stops_without_sampling_or_eviction(tmp_path, already_quarantined):
    box = Outbox(tmp_path / "queue.sqlite", uuid4(), max_records=1)
    message = packet(box.device_id)
    box.enqueue(message.to_bytes())
    if already_quarantined:
        box.quarantine(str(message.message_id), "http_409")
    calls = []

    def reader():
        calls.append(True)
        return {"test_sensor": 42}

    sender = SimpleNamespace(send=lambda body: Delivery("quarantine", "http_409"))
    with pytest.raises(OutboxFull):
        run_agent(box, sender, reader, count=1, drain_seconds=0)
    assert calls == []
    with sqlite3.connect(box.path) as db:
        assert db.execute("SELECT body, state FROM messages").fetchall() == [
            (message.to_bytes(), "quarantined")]


def test_full_startup_propagates_fatal_sender_failure(tmp_path):
    box = Outbox(tmp_path / "queue.sqlite", uuid4(), max_records=1)
    message = packet(box.device_id)
    box.enqueue(message.to_bytes())
    calls = []
    failure = FatalDelivery("test operator intervention")

    def send(body):
        raise failure

    def reader():
        calls.append(True)
        return {"test_sensor": 42}

    with pytest.raises(FatalDelivery) as caught:
        run_agent(box, SimpleNamespace(send=send), reader, count=1, drain_seconds=0)
    assert caught.value is failure
    assert calls == []
    assert box.oldest() == (str(message.message_id), message.to_bytes())


def test_full_startup_retries_identical_packet_before_sampling(tmp_path):
    box = Outbox(tmp_path / "queue.sqlite", uuid4(), max_records=1)
    message = packet(box.device_id)
    box.enqueue(message.to_bytes())
    attempts, readings = [], []

    def send(body):
        attempts.append(body)
        return Delivery("retry") if len(attempts) == 1 else Delivery("ack")

    def reader():
        readings.append(len(attempts))
        return {"test_sensor": 42}

    assert run_agent(box, SimpleNamespace(send=send), reader, count=1, drain_seconds=2) == {}
    assert readings == [2]
    assert attempts[:2] == [message.to_bytes(), message.to_bytes()]
    assert len(attempts) == 3


def test_new_overflow_during_collection_still_stops_without_eviction(tmp_path):
    box = Outbox(tmp_path / "queue.sqlite", uuid4(), max_records=1)
    readings = []

    def reader():
        readings.append(len(readings) + 1)
        return {"test_sensor": readings[-1]}

    sender = SimpleNamespace(send=lambda body: Delivery("retry"))
    with pytest.raises(OutboxFull):
        run_agent(box, sender, reader, interval=0.001, count=2, drain_seconds=0)
    assert readings == [1, 2]
    retained = TelemetryV1.parse(box.oldest()[1])
    assert retained.payload == {"test_sensor": 1}
    assert retained.sequence_no == 1
    assert box.counts() == {"pending": 1}
