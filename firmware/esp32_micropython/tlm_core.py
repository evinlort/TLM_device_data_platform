"""Portable MicroPython core. No hardware, networking, or server dependencies."""
import binascii
import hashlib
import json
import math
import os

PERIOD_MS = 10000
MAX_MESSAGE_BYTES = 8192  # ESP32 pilot limit, stricter than the API's 64 KiB.
_ALNUM = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


class QueueFull(Exception):
    pass


class QueueCorrupt(Exception):
    pass


def canonical_uuid(value):
    if not isinstance(value, str) or len(value) != 36:
        raise ValueError("Expected canonical UUID")
    value = value.lower()
    for index, char in enumerate(value):
        if index in (8, 13, 18, 23):
            if char != "-":
                raise ValueError("Expected canonical UUID")
        elif char not in "0123456789abcdef":
            raise ValueError("Expected canonical UUID")
    return value


def uuid4(random_bytes=os.urandom):
    raw = bytearray(random_bytes(16))
    if len(raw) != 16:
        raise ValueError("Random source must return 16 bytes")
    raw[6] = (raw[6] & 15) | 64
    raw[8] = (raw[8] & 63) | 128
    text = binascii.hexlify(raw).decode()
    return "-".join((text[:8], text[8:12], text[12:16], text[16:20], text[20:]))


def make_message(device_id, stream_id, sequence_no, payload, message_id, captured_at=None):
    if type(sequence_no) is not int or not 1 <= sequence_no < 2**63:
        raise ValueError("Invalid sequence number")
    if not isinstance(payload, dict) or not 1 <= len(payload) <= 128:
        raise ValueError("Expected 1..128 readings")
    for name, value in payload.items():
        if (not isinstance(name, str) or not 1 <= len(name) <= 64
                or name[0] not in _ALNUM
                or any(c not in _ALNUM + "_.-" for c in name)):
            raise ValueError("Invalid sensor name")
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError("Expected finite numeric reading")
    # This client intentionally sends null until an operator enables trusted time.
    if captured_at is not None:
        raise ValueError("This ESP32 pilot uses captured_at=null")
    message = {
        "schema_version": 1, "device_id": canonical_uuid(device_id),
        "message_id": canonical_uuid(message_id), "stream_id": canonical_uuid(stream_id),
        "sequence_no": sequence_no, "captured_at": None, "payload": payload,
    }
    body = json.dumps(message).encode("utf-8")
    if len(body) > MAX_MESSAGE_BYTES:
        raise ValueError("Message too large for ESP32 pilot")
    return body


def _digest(body):
    return binascii.hexlify(hashlib.sha256(body).digest())


def _exists(path):
    try:
        os.stat(path)
        return True
    except OSError as error:
        if error.args[0] != 2:
            raise
        return False


def _sync_directory(path):
    if hasattr(os, "fsync"):
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    else:
        os.sync()


def _write(path, data):
    with open(path, "wb") as stream:
        stream.write(data)
        stream.flush()
        if hasattr(os, "fsync"):
            os.fsync(stream.fileno())
    if not hasattr(os, "fsync"):
        os.sync()


class FileOutbox:
    """Single-owner, single-event-loop LittleFS queue; never format on failure.

    Checksummed staging files are renamed only after flush. Completed staging
    files are recovered after restart. Corrupt data requires operator action.
    This is not certification of flash endurance or sudden-power-loss behavior.
    """

    def __init__(self, directory, device_id, capacity=512):
        if type(capacity) is not int or not 1 <= capacity <= 4096:
            raise ValueError("Invalid queue capacity")
        self.directory = directory
        self.device_id = canonical_uuid(device_id)
        self.capacity = capacity
        if not _exists(directory):
            os.mkdir(directory)
        owner = directory + "/owner"
        staged_owner = directory + "/owner.tmp"
        if not _exists(owner):
            if any(name != "owner.tmp" for name in os.listdir(directory)):
                raise QueueCorrupt("Queue owner missing; preserve directory")
            if _exists(staged_owner):
                with open(staged_owner, "rb") as stream:
                    if stream.read() != self.device_id.encode():
                        raise QueueCorrupt("Incomplete queue owner")
            else:
                _write(staged_owner, self.device_id.encode())
            os.rename(staged_owner, owner)
            _sync_directory(directory)
        with open(owner, "rb") as stream:
            if stream.read() != self.device_id.encode():
                raise ValueError("Queue belongs to another device")
        self._recover()

    def _names(self):
        result = []
        for name in os.listdir(self.directory):
            if name == "owner":
                continue
            self._validate_name(name)
            result.append(name)
        return sorted(result)

    @staticmethod
    def _validate_name(name):
        if (len(name) != 20 or name[-4:] not in (".msg", ".bad", ".tmp")
                or any(c not in "0123456789" for c in name[:16])):
            raise QueueCorrupt("Unexpected queue file; preserve directory")

    def _read(self, name):
        self._validate_name(name)
        with open(self.directory + "/" + name, "rb") as stream:
            record = stream.read(MAX_MESSAGE_BYTES + 66)
        if len(record) < 66 or len(record) > MAX_MESSAGE_BYTES + 65:
            raise QueueCorrupt("Invalid queue record size")
        checksum, body = record[:64], record[65:]
        if record[64:65] != b"\n" or checksum != _digest(body):
            raise QueueCorrupt("Queue checksum mismatch")
        try:
            message = json.loads(body)
            if message["device_id"] != self.device_id:
                raise ValueError("Wrong device")
        except (ValueError, TypeError, KeyError):
            raise QueueCorrupt("Invalid queue message")
        return body

    def _recover(self):
        for name in self._names():
            if name.endswith(".tmp"):
                body = self._read(name)
                target = name[:-4] + ".msg"
                if _exists(self.directory + "/" + target):
                    if self._read(target) != body:
                        raise QueueCorrupt("Ambiguous interrupted write")
                    os.remove(self.directory + "/" + name)
                else:
                    os.rename(self.directory + "/" + name, self.directory + "/" + target)
                _sync_directory(self.directory)

    def enqueue(self, body):
        names = self._names()
        if len(names) >= self.capacity:
            raise QueueFull("Outbox full; existing messages retained")
        if not isinstance(body, bytes) or not 0 < len(body) <= MAX_MESSAGE_BYTES:
            raise ValueError("Invalid message bytes")
        if json.loads(body).get("device_id") != self.device_id:
            raise ValueError("Message belongs to another device")
        number = max([int(name[:16]) for name in names] or [0]) + 1
        if number >= 10**16:
            raise QueueFull("Queue index exhausted")
        stem = self.directory + "/%016d" % number
        _write(stem + ".tmp", _digest(body) + b"\n" + body)
        os.rename(stem + ".tmp", stem + ".msg")
        _sync_directory(self.directory)

    def peek(self):
        for name in self._names():
            if name.endswith(".msg"):
                return name, self._read(name)
        return None

    def ack(self, name, expected_body):
        if not name.endswith(".msg") or self._read(name) != expected_body:
            raise QueueCorrupt("ACK does not match queued bytes")
        os.remove(self.directory + "/" + name)
        _sync_directory(self.directory)

    def quarantine(self, name):
        self._read(name)
        if not name.endswith(".msg"):
            raise QueueCorrupt("Not a pending record")
        os.rename(self.directory + "/" + name,
                  self.directory + "/" + name[:-4] + ".bad")
        _sync_directory(self.directory)


class Cadence:
    def __init__(self, start_ms, ticks_add, ticks_diff):
        self.next_ms = start_ms
        self.add = ticks_add
        self.diff = ticks_diff

    def due(self, now_ms):
        late = self.diff(now_ms, self.next_ms)
        if late < 0:
            return False
        periods = late // PERIOD_MS + 1
        self.next_ms = self.add(self.next_ms, periods * PERIOD_MS)
        return True


def response_action(status, response_body, message_body):
    if status in (200, 201):
        try:
            ack = json.loads(response_body)
            message = json.loads(message_body)
            label = "stored" if status == 201 else "duplicate"
            if (isinstance(ack, dict) and ack.get("status") == label
                    and ack.get("device_id") == message["device_id"]
                    and ack.get("message_id") == message["message_id"]
                    and isinstance(ack.get("received_at"), str) and ack["received_at"]):
                return "ack"
        except (ValueError, TypeError, KeyError):
            pass
        return "retry"
    if status in (400, 409, 413, 422):
        return "quarantine"
    if 300 <= status < 400 or status in (401, 403, 404, 405, 415):
        return "fatal"
    return "retry"


def retry_seconds(attempt, retry_after):
    delay = min(60, 2 ** min(max(0, attempt), 6))
    if isinstance(retry_after, str) and retry_after and len(retry_after) <= 10:
        if all(c in "0123456789" for c in retry_after):
            delay = max(delay, min(300, int(retry_after)))
    return delay
