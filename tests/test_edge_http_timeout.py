"""Regression tests for Linux edge HTTP timeout and coordinated shutdown."""
from __future__ import annotations

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import inspect
import json
import math
import sqlite3
from threading import Event, Lock, Thread
import time
from types import SimpleNamespace
from uuid import uuid4

import pytest

import tlm_device_data_platform.edge_agent as edge_agent
from tlm_device_data_platform.edge_agent import (
    Delivery, FatalDelivery, HTTPSender, Outbox, deliver_one, run_agent,
)
from tlm_device_data_platform.telemetry_v1 import TelemetryV1


TOKEN = "a" * 43


def packet(device_id, *, sequence_no=1):
    return TelemetryV1(
        device_id, uuid4(), uuid4(), sequence_no, None, {"test_sensor": 12.5}
    )


class Response(io.BytesIO):
    status = 201
    headers = {}


def receipt(message, status):
    return json.dumps({
        "device_id": str(message.device_id),
        "message_id": str(message.message_id),
        "received_at": "2026-10-02T00:00:00+00:00",
        "status": status,
    }).encode()


def test_default_timeout_is_fifteen_seconds_and_existing_constructor_still_works():
    sender = HTTPSender("https://example.invalid/v1/telemetry", TOKEN)
    message = packet(uuid4())
    observed = []

    def open_request(request, *, timeout):
        observed.append(timeout)
        return Response(receipt(message, "stored"))

    sender._opener = SimpleNamespace(open=open_request)
    assert sender.send(message.to_bytes()) == Delivery("ack")
    assert observed == [15.0]
    assert inspect.signature(run_agent).parameters["drain_seconds"].default == 15.0


@pytest.mark.parametrize(
    "value",
    [0, -0.1, math.nan, math.inf, -math.inf, True, False],
)
def test_timeout_must_be_positive_finite_number(value):
    with pytest.raises(ValueError, match="timeout_seconds"):
        HTTPSender(
            "https://example.invalid/v1/telemetry", TOKEN, timeout_seconds=value
        )


@contextmanager
def delayed_ack_server(delays, statuses):
    state = SimpleNamespace(
        delays=iter(delays),
        statuses=iter(statuses),
        requests=[],
        started=Event(),
        lock=Lock(),
    )

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_POST(self):
            length = int(self.headers["Content-Length"])
            body = self.rfile.read(length)
            message = TelemetryV1.parse(body)
            with state.lock:
                state.requests.append(body)
                delay = next(state.delays)
                status = next(state.statuses)
            state.started.set()
            time.sleep(delay)
            payload = receipt(message, "stored" if status == 201 else "duplicate")
            try:
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(payload)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, format, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server_thread = Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    try:
        yield (
            f"http://127.0.0.1:{server.server_port}/v1/telemetry",
            state,
        )
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=2)
        assert not server_thread.is_alive(), "Test HTTP server did not stop"


def test_default_timeout_accepts_ack_delayed_by_six_seconds(tmp_path):
    box = Outbox(tmp_path / "queue.sqlite", uuid4())
    message = packet(box.device_id)
    box.enqueue(message.to_bytes())

    with delayed_ack_server([6.0], [201]) as (url, state):
        sender = HTTPSender(url, TOKEN, allow_insecure_http=True)
        assert deliver_one(box, sender) == Delivery("ack")

    assert state.requests == [message.to_bytes()]
    assert box.counts() == {}


def test_timeout_replay_preserves_exact_packet_and_deletes_only_confirmed_message(
    tmp_path,
):
    box = Outbox(tmp_path / "queue.sqlite", uuid4())
    first = packet(box.device_id)
    second = packet(box.device_id, sequence_no=2)
    box.enqueue(first.to_bytes())
    box.enqueue(second.to_bytes())

    with delayed_ack_server([0.2, 0.0], [201, 200]) as (url, state):
        sender = HTTPSender(
            url, TOKEN, allow_insecure_http=True, timeout_seconds=0.05
        )
        assert deliver_one(box, sender) == Delivery("retry", "network_error")
        with sqlite3.connect(box.path) as database:
            retained = database.execute(
                "SELECT message_id, body FROM messages ORDER BY id"
            ).fetchall()
        assert retained == [
            (str(first.message_id), first.to_bytes()),
            (str(second.message_id), second.to_bytes()),
        ]

        assert deliver_one(box, sender) == Delivery("ack")

    assert state.requests == [first.to_bytes(), first.to_bytes()]
    assert box.oldest() == (str(second.message_id), second.to_bytes())
    assert box.counts() == {"pending": 1}


def test_count_one_waits_for_active_sender_and_returns_clean_queue(tmp_path):
    box = Outbox(tmp_path / "queue.sqlite", uuid4())
    send_started = Event()

    def send(body):
        send_started.set()
        time.sleep(0.2)
        return Delivery("ack")

    counts = run_agent(
        box,
        SimpleNamespace(send=send),
        lambda: {"test_sensor": 1},
        count=1,
        drain_seconds=1,
    )

    assert send_started.is_set()
    assert counts == {}


def test_shutdown_during_request_cannot_mutate_queue_after_return(tmp_path, monkeypatch):
    monkeypatch.setattr(edge_agent, "SENDER_JOIN_TIMEOUT_SECONDS", 0.05)
    acknowledge_called = Event()

    class ObservedOutbox(Outbox):
        def acknowledge(self, message_id):
            acknowledge_called.set()
            super().acknowledge(message_id)

    box = ObservedOutbox(tmp_path / "queue.sqlite", uuid4())
    request_started = Event()
    release_request = Event()
    send_finished = Event()
    failures = []

    def send(body):
        request_started.set()
        assert release_request.wait(2), "Test did not release the sender"
        send_finished.set()
        return Delivery("ack")

    def agent():
        try:
            run_agent(
                box,
                SimpleNamespace(send=send),
                lambda: {"test_sensor": 1},
                count=1,
                drain_seconds=0.2,
            )
        except BaseException as error:
            failures.append(error)

    thread = Thread(target=agent, daemon=True)
    thread.start()
    assert request_started.wait(2)
    thread.join(timeout=1)
    assert not thread.is_alive(), "Agent did not complete bounded shutdown"
    assert len(failures) == 1
    assert isinstance(failures[0], FatalDelivery)
    original = box.oldest()
    assert original is not None

    release_request.set()
    assert send_finished.wait(1)
    assert not acknowledge_called.wait(0.2)

    assert box.oldest() == original
    assert box.counts() == {"pending": 1}
