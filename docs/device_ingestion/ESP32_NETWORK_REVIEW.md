# ESP32 network review fixes

## Scope and ownership

The starting point is PR #3 head `370f2473f4b77b6309cb716c3fc09a0762689b85`.
User-authorized follow-up fixes blocking DNS/NTP preparation and ambiguous IPv4
text in the opt-in HTTP path. No API contract, SQL, token, queue format, sensor
wiring, sampling period, or existing test assertion is changed.

`main.start()` creates exactly one `NetworkWorker`, injects its resolver into
`HTTPTransport`, and uses the same worker for NTP. A locked one-slot mailbox is
polled by the asyncio owner. The worker never calls asyncio, accesses the
outbox, sets the RTC, or receives device tokens. The queue remains single-owner.

A job has a unique ticket. Its caller can time out or be cancelled; the native
operation is not killed or replaced. Until it finishes, new work fails with a
retryable busy error rather than spawning another thread or growing a backlog.
Late results are discarded. NTP returns epoch seconds; only a live successful
caller sets the RTC. Clock readiness still fails closed, NTP retries remain
throttled, and `captured_at` remains null.

DNS returns an IPv4 address. The TCP connector receives canonical numeric IPv4,
so its internal getaddrinfo does not perform another network name lookup.
TLS uses the original API hostname for certificate verification/SNI; HTTP Host
also remains the original authority. No certificate verification is disabled.
The HTTP opt-in rejects leading zeros and other noncanonical IPv4 spellings.

## Lifecycle and limits

Worker jobs have a 5-second async waiting limit. NTP's UDP receive has its
existing 2-second timeout, which is not a DNS deadline. Shutdown signals the
worker and waits up to 3 seconds. A native call may outlive both limits: its
result is discarded and the thread exits when the call returns. After the
`network_worker_busy` shutdown message, reset the board before starting again.
There is no automatic worker replacement, hard thread kill, queue deletion,
or credential regeneration.

Native ESP32 DNS/socket waits release the interpreter lock in the pinned port.
The fix isolates those waits; it is not a hard-real-time guarantee for sensor
reads, Wi-Fi operations, flash, garbage collection, or CPU-bound native calls.
MicroPython documents `_thread` as experimental. ESP32 execution, Wi-Fi behavior,
flash endurance, and physical power-loss behavior still need hardware acceptance.

## Regression validation

`tests/test_esp32_network_review.py` uses the exact firmware and real host
threads. The collection tests run `tlm_runtime.run` with real FileOutbox writes
while a DNS/NTP fixture blocks in the worker. Only the cadence is accelerated;
readings and network operations are explicitly controlled software fixtures.
They verify persisted sequences and unchanged queued bytes before transport.

Other cases cover timeout/cancellation, busy retries, a single worker thread,
late NTP answers, shutdown, recoverable worker failure, boot wiring, clock
readiness/backoff, canonical IPv4, and original TLS hostname/Host preservation.
No test contacts an external endpoint or uses real credentials. These host
tests complement, not replace, the existing HTTP/TLS and PostgreSQL tests.
The firmware workflow now requires all six USB source modules to compile.

Run the full installed package suite and pinned disposable-Supabase workflow
as documented in STAND_SETUP.md. Use exact-HEAD PR checks and artifacts for
results; a previous successful SHA does not validate a later commit.

## Primary sources

- [Pinned asyncio implementation](https://github.com/micropython/micropython/blob/0fd6c573ea815774668bbb16b8e197c8822368b2/extmod/asyncio/stream.py): blocking DNS, nonblocking socket, supported server_hostname.
- [Pinned ESP32 sockets](https://github.com/micropython/micropython/blob/0fd6c573ea815774668bbb16b8e197c8822368b2/ports/esp32/modsocket.c): interpreter-lock release around native network waits.
- [Pinned ntptime](https://github.com/micropython/micropython-lib/blob/ee4bb8ff139e24c42b739935fbd8ec7c4d061e02/micropython/net/ntptime/ntptime.py): DNS precedes socket timeout; time() does not set RTC.
- [MicroPython asyncio](https://docs.micropython.org/en/v1.29.0/library/asyncio.html): cooperative scheduling and cross-thread signaling limits.
- [MicroPython threads](https://docs.micropython.org/en/v1.29.0/library/_thread.html): experimental API.
- [MicroPython TLS](https://docs.micropython.org/en/v1.29.0/library/ssl.html): certificate verification and server_hostname.
