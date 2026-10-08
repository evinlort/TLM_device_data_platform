"""Durable session context, refreshed separately from Linux sensor collection."""
from dataclasses import dataclass
import json
from threading import Lock
from uuid import UUID


@dataclass(frozen=True)
class DeviceContext:
    device_id: UUID
    session_id: UUID | None
    revision: int

    def to_bytes(self):
        return json.dumps({'device_id': str(self.device_id),
                           'session_id': str(self.session_id) if self.session_id else None,
                           'revision': self.revision}, sort_keys=True).encode()

    @classmethod
    def parse(cls, body, device_id):
        data = json.loads(body)
        if not isinstance(data, dict) or set(data) != {'device_id', 'session_id', 'revision'}:
            raise ValueError('Invalid device context')
        if UUID(data['device_id']) != device_id or type(data['revision']) is not int or not 0 <= data['revision'] < 2**63:
            raise ValueError('Invalid device context identity or revision')
        return cls(device_id, UUID(data['session_id']) if data['session_id'] is not None else None, data['revision'])


class ContextPending(RuntimeError):
    """Collection waits for initial context or a detected reconnection refresh."""


class ContextTracker:
    def __init__(self, outbox, sender):
        self._outbox, self._sender = outbox, sender
        self._context = outbox.load_context()
        self._lock = Lock()
        self._closed = False
        self._offline = False
        self._startup = True
        self._required = True

    def current(self):
        with self._lock:
            if self._required or self._context is None:
                raise ContextPending(
                    'Confirmed device context required before collection')
            return self._context

    def observe_delivery(self):
        with self._lock:
            if self._offline:
                self._required = True

    def close(self):
        with self._lock:
            self._closed = True

    def refresh(self):
        try:
            context = self._sender.context(self._outbox.device_id)
        except OSError:
            with self._lock:
                self._offline = True
                if self._startup and self._context is not None:
                    self._required, self._startup = False, False
            return False
        with self._lock:
            if self._closed:
                return False
            self._outbox.save_context(context)
            self._context, self._offline, self._required = context, False, False
            self._startup = False
        return True
