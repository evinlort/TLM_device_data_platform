"""Linux edge agent: explicit sensor adapter, durable outbox, independent sender."""
from __future__ import annotations

import argparse
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from http.client import HTTPException
import importlib
import json
import logging
import math
import os
from pathlib import Path
import re
import sqlite3
import ssl
from threading import Event, Lock, Thread
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener
from uuid import UUID, uuid4

from .telemetry_v1 import TelemetryV1
from .private_config import load_private_config

_LOG = logging.getLogger(__name__)
DEFAULT_HTTP_TIMEOUT_SECONDS = 15.0
SENDER_POLL_SECONDS = 0.1
DEFAULT_DRAIN_GRACE_SECONDS = 1.0
DEFAULT_DRAIN_SECONDS = DEFAULT_HTTP_TIMEOUT_SECONDS + DEFAULT_DRAIN_GRACE_SECONDS
SENDER_JOIN_TIMEOUT_SECONDS = 6.0


class OutboxFull(RuntimeError):
    """Stop collection rather than silently discard unacknowledged records."""


class FatalDelivery(RuntimeError):
    """Operator action is required; preserve all queued messages."""


class Outbox:
    def __init__(self, path: Path, device_id: UUID, max_records: int = 10000):
        if max_records < 1:
            raise ValueError("max_records must be positive")
        self.path, self.device_id, self.max_records = Path(path), device_id, max_records
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.path.is_symlink():
            raise ValueError("Outbox must not be a symlink")
        try:
            os.close(os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600))
        except FileExistsError:
            pass
        with closing(self._connect()) as db, db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                       "message_id TEXT NOT NULL UNIQUE, body BLOB NOT NULL, "
                       "state TEXT NOT NULL DEFAULT 'pending', error TEXT)")
            db.execute("INSERT OR IGNORE INTO metadata VALUES ('device_id', ?)", (str(device_id),))
            if db.execute("SELECT value FROM metadata WHERE key='device_id'").fetchone()[0] != str(device_id):
                raise ValueError("Outbox belongs to another device")

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.execute("PRAGMA synchronous=FULL")
        return db

    def enqueue(self, body: bytes) -> None:
        message = TelemetryV1.parse(body)
        if message.device_id != self.device_id:
            raise ValueError("Outbox device mismatch")
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT count(*) FROM messages").fetchone()[0] >= self.max_records:
                raise OutboxFull
            db.execute("INSERT INTO messages (message_id, body) VALUES (?, ?)",
                       (str(message.message_id), body))

    def oldest(self) -> tuple[str, bytes] | None:
        with closing(self._connect()) as db:
            return db.execute("SELECT message_id, body FROM messages WHERE state='pending' ORDER BY id LIMIT 1").fetchone()

    def acknowledge(self, message_id: str) -> None:
        with closing(self._connect()) as db, db:
            db.execute("DELETE FROM messages WHERE message_id=? AND state='pending'", (message_id,))

    def quarantine(self, message_id: str, reason: str) -> None:
        with closing(self._connect()) as db, db:
            db.execute("UPDATE messages SET state='quarantined', error=? WHERE message_id=?",
                       (reason, message_id))

    def counts(self) -> dict[str, int]:
        with closing(self._connect()) as db:
            return dict(db.execute("SELECT state, count(*) FROM messages GROUP BY state"))


class _NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass(frozen=True)
class Delivery:
    action: str
    reason: str = ""
    retry_after: float = 0


class HTTPSender:
    def __init__(self, url: str, token: str, *, allow_insecure_http: bool = False,
                 timeout_seconds: float = DEFAULT_HTTP_TIMEOUT_SECONDS):
        parsed = urlsplit(url)
        if (not parsed.hostname or parsed.username or parsed.password or parsed.query
                or parsed.fragment or parsed.path != "/v1/telemetry"
                or any(c in url for c in "\r\n")):
            raise ValueError("Invalid telemetry endpoint")
        if parsed.scheme != "https" and not (allow_insecure_http and parsed.scheme == "http"):
            raise ValueError("HTTPS required; insecure HTTP is an explicit isolated-lab option")
        if not re.fullmatch(r"[A-Za-z0-9_-]{43,128}", token):
            raise ValueError("Invalid device token format")
        if (isinstance(timeout_seconds, bool)
                or not isinstance(timeout_seconds, (int, float))
                or not math.isfinite(timeout_seconds)
                or timeout_seconds <= 0):
            raise ValueError("timeout_seconds must be a positive finite number")
        self._url, self._token = url, token
        self._timeout_seconds = float(timeout_seconds)
        self._opener = build_opener(_NoRedirects(), HTTPSHandler(context=ssl.create_default_context()))

    def send(self, body: bytes) -> Delivery:
        message = TelemetryV1.parse(body)
        request = Request(self._url, data=body, method="POST", headers={
            "Authorization": f"Bearer {self._token}", "Content-Type": "application/json"})
        try:
            try:
                response = self._opener.open(request, timeout=self._timeout_seconds)
            except HTTPError as error:
                response = error
            with response:
                status = response.status
                if status in (200, 201):
                    raw = response.read(4097)
                    try:
                        receipt = json.loads(raw) if len(raw) <= 4096 else {}
                        valid = (isinstance(receipt, dict)
                            and receipt.get("device_id") == str(message.device_id)
                            and receipt.get("message_id") == str(message.message_id)
                            and receipt.get("status") == ("stored" if status == 201 else "duplicate")
                            and isinstance(receipt.get("received_at"), str))
                    except (ValueError, UnicodeError):
                        valid = False
                    return Delivery("ack" if valid else "retry", "invalid_receipt" if not valid else "")
                if status in (408, 429) or 500 <= status <= 599:
                    retry_after = response.headers.get("Retry-After", "")
                    delay = min(int(retry_after), 3600) if retry_after.isdigit() and len(retry_after) < 8 else 0
                    return Delivery("retry", f"http_{status}", delay)
                if status in (400, 409, 413, 422):
                    return Delivery("quarantine", f"http_{status}")
                raise FatalDelivery("Credential, endpoint or redirect rejected; queue preserved")
        except (URLError, HTTPException, TimeoutError, OSError) as error:
            reason = error.reason if isinstance(error, URLError) else error
            if isinstance(reason, ssl.SSLCertVerificationError):
                raise FatalDelivery("TLS certificate verification failed; queue preserved") from error
            return Delivery("retry", "network_error")


def deliver_one(outbox: Outbox, sender: HTTPSender) -> Delivery:
    item = outbox.oldest()
    if item is None:
        return Delivery("idle")
    message_id, body = item
    result = sender.send(body)
    if result.action == "ack":
        outbox.acknowledge(message_id)
    elif result.action == "quarantine":
        outbox.quarantine(message_id, result.reason)
        _LOG.error("Message %s quarantined (%s)", message_id, result.reason)
    return result


def load_sensor(spec: str):
    """Load an explicitly selected, locally installed hardware reader."""
    module, separator, name = spec.partition(":")
    if not separator or not module or not name:
        raise ValueError("Sensor must be specified as module:function")
    reader = getattr(importlib.import_module(module), name)
    if not callable(reader):
        raise ValueError("Sensor adapter is not callable")
    return reader


def run_agent(outbox, sender, reader, *, interval=10.0, count=0,
              synchronized_clock=True, drain_seconds=DEFAULT_DRAIN_SECONDS):
    if interval <= 0 or count < 0 or drain_seconds < 0:
        raise ValueError("Invalid collection settings")
    stop, failures, queue_access = Event(), [], Lock()

    def transmit():
        backoff = 1.0
        try:
            while not stop.is_set():
                with queue_access:
                    item = outbox.oldest()
                if item is None:
                    result = Delivery("idle")
                else:
                    message_id, body = item
                    result = sender.send(body)
                    with queue_access:
                        if stop.is_set():
                            break
                        if result.action == "ack":
                            outbox.acknowledge(message_id)
                        elif result.action == "quarantine":
                            outbox.quarantine(message_id, result.reason)
                            _LOG.error("Message %s quarantined (%s)",
                                       message_id, result.reason)
                if result.action == "retry":
                    stop.wait(max(backoff, result.retry_after))
                    backoff = min(backoff * 2, 60)
                else:
                    backoff = 1
                    if result.action == "idle":
                        stop.wait(SENDER_POLL_SECONDS)
        except Exception as error:
            failures.append(error)
            stop.set()

    worker = Thread(target=transmit, daemon=True)
    worker.start()
    try:
        # A recovered full queue must free a durable slot before the first sample.
        while not stop.is_set():
            with queue_access:
                counts = outbox.counts()
            if sum(counts.values()) < outbox.max_records:
                break
            if not counts.get("pending"):
                raise OutboxFull("Outbox full with no pending records; operator action required")
            stop.wait(SENDER_POLL_SECONDS)
        stream_id, sequence_no, deadline = uuid4(), 1, time.monotonic()
        while not stop.is_set() and (count == 0 or sequence_no <= count):
            if stop.wait(max(0, deadline - time.monotonic())):
                break
            readings = reader()
            captured = datetime.now(timezone.utc) if synchronized_clock else None
            message = TelemetryV1(outbox.device_id, uuid4(), stream_id, sequence_no, captured, readings)
            with queue_access:
                outbox.enqueue(message.to_bytes())
            sequence_no += 1
            deadline += interval
            if deadline < time.monotonic():
                deadline = time.monotonic() + interval
        drain_until = time.monotonic() + drain_seconds
        while not stop.is_set() and time.monotonic() < drain_until:
            with queue_access:
                pending = outbox.oldest()
            if pending is None:
                break
            stop.wait(SENDER_POLL_SECONDS)
    finally:
        stop.set()
        # Wait for any current SQLite mutation. A sender still blocked in I/O will
        # observe stop before applying its result, so queue ownership can be released.
        with queue_access:
            pass
        worker.join(timeout=SENDER_JOIN_TIMEOUT_SECONDS)
    if failures:
        raise failures[0]
    if worker.is_alive():
        raise FatalDelivery("Sender did not stop; queue remains durable")
    return outbox.counts()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, help="Private device JSON configuration")
    parser.add_argument("--sensor", required=True, help="Installed module:function returning numeric readings")
    parser.add_argument("--api-url", default=os.environ.get("TLM_API_URL"))
    parser.add_argument("--device-id", default=os.environ.get("TLM_DEVICE_ID"))
    parser.add_argument("--outbox", type=Path, default=Path.home() / ".local/state/tlm/outbox.sqlite3")
    parser.add_argument("--count", type=int, default=0, help="0 means continuous collection")
    parser.add_argument("--max-records", type=int, default=10000)
    parser.add_argument("--unsynchronized-clock", action="store_true")
    parser.add_argument("--allow-insecure-http", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    try:
        import fcntl  # The supplied executable agent targets Linux, not ESP32 firmware.
        config = (load_private_config(args.config, {"TLM_DEVICE_ID", "TLM_DEVICE_TOKEN", "TLM_API_URL"})
                  if args.config else {})
        api_url = args.api_url or config.get("TLM_API_URL")
        device_id = args.device_id or config.get("TLM_DEVICE_ID")
        token = config.get("TLM_DEVICE_TOKEN") or os.environ.get("TLM_DEVICE_TOKEN")
        if not api_url or not device_id or not token:
            raise ValueError("API URL, device ID and private device token are required")
        reader = load_sensor(args.sensor)
        outbox = Outbox(args.outbox, UUID(device_id), args.max_records)
        lock_fd = os.open(str(args.outbox) + ".lock", os.O_CREAT | os.O_RDWR, 0o600)
        with os.fdopen(lock_fd, "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            sender = HTTPSender(api_url, token,
                                allow_insecure_http=args.allow_insecure_http)
            counts = run_agent(outbox, sender, reader, count=args.count,
                               synchronized_clock=not args.unsynchronized_clock)
            _LOG.info("Remaining outbox records by state: %s", counts)
            return 0 if not counts else 2
    except KeyboardInterrupt:
        return 130
    except Exception as error:
        _LOG.error("Agent stopped (%s); unacknowledged records retained", type(error).__name__)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
