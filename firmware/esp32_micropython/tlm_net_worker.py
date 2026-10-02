"""One bounded DNS/NTP worker; queue, RTC and asyncio stay in the owner thread."""
import _thread
import asyncio
import time


def _lookup_ipv4(host, port):
    import socket
    return socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)[0][-1][0]


def _read_ntp_time(host):
    import ntptime
    ntptime.host = host
    ntptime.timeout = 2
    # Return epoch seconds only. Never let a late job mutate the device RTC.
    return ntptime.time()


class NetworkWorker:
    """Single flight, no waiting-job backlog and no replacement on timeout.

    Only the worker executes blocking operations. A lock protects a one-slot
    mailbox; the owner polls cooperatively, so no thread calls asyncio APIs.
    Native DNS can outlive a coroutine timeout. Keep that slot occupied until
    it actually finishes, and discard its result if its caller has left.
    """

    def __init__(self):
        self._lock = _thread.allocate_lock()
        self._job = None
        self._result = None
        self._waiting = None
        self._serial = 0
        self._closed = False
        self._stopped = False
        _thread.start_new_thread(self._serve, ())

    def _serve(self):
        try:
            while True:
                with self._lock:
                    if self._closed:
                        return
                    job = self._job
                if job is None:
                    time.sleep(0.01)
                    continue
                ticket, function, args = job
                try:
                    value = function(*args)
                    ok = True
                except Exception:
                    # Do not transfer tracebacks or network/configuration details.
                    value, ok = None, False
                with self._lock:
                    self._job = None
                    if not self._closed and self._waiting == ticket:
                        self._result = (ticket, ok, value)
                job = function = args = value = None
        finally:
            with self._lock:
                self._job = None
                self._stopped = True

    def idle(self):
        with self._lock:
            return self._job is None and self._waiting is None

    async def _receive(self, ticket):
        while True:
            with self._lock:
                if self._closed or self._stopped:
                    raise OSError('Network worker closed')
                result = self._result
            if result is not None and result[0] == ticket:
                if not result[1]:
                    raise OSError('Network preparation failed')
                return result[2]
            await asyncio.sleep(0.01)

    async def call(self, function, *args, timeout=5):
        if timeout <= 0:
            raise ValueError('Worker timeout must be positive')
        with self._lock:
            if self._closed or self._stopped:
                raise OSError('Network worker closed')
            if self._job is not None or self._waiting is not None:
                raise OSError('Network worker busy')
            self._serial += 1
            ticket = self._serial
            self._waiting = ticket
            self._result = None
            self._job = (ticket, function, args)
        try:
            return await asyncio.wait_for(self._receive(ticket), timeout)
        finally:
            with self._lock:
                if self._waiting == ticket:
                    self._waiting = None
                    self._result = None

    async def resolve_ipv4(self, host, port):
        return await self.call(_lookup_ipv4, host, port)

    async def ntp_time(self, host):
        return await self.call(_read_ntp_time, host)

    def close(self):
        # A running native call cannot be killed safely; discard it on return.
        with self._lock:
            self._closed = True
            self._result = None

    async def wait_closed(self, timeout=3):
        async def stopped():
            while True:
                with self._lock:
                    if self._stopped:
                        return
                await asyncio.sleep(0.01)
        await asyncio.wait_for(stopped(), timeout)
