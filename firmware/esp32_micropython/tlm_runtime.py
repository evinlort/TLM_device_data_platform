"""Sequential persist-then-ACK runtime, with no Linux-only dependencies."""
import asyncio

from hcsr04 import SensorReadError
from tlm_core import Cadence, make_message, response_action, retry_seconds, uuid4

_running = False


def runtime_active():
    return _running


def sample_once(queue, sensor, device_id, stream_id, sequence_no, new_id=uuid4):
    readings = sensor.read()
    body = make_message(device_id, stream_id, sequence_no, readings, new_id())
    queue.enqueue(body)
    return body


async def send_once(queue, transport, log=None):
    item = queue.peek()
    if item is None:
        return "empty", None
    name, body = item
    try:
        status, headers, response = await transport.post(body)
    except (OSError, EOFError, ValueError, asyncio.TimeoutError) as error:
        if log is not None:
            if isinstance(error, asyncio.TimeoutError):
                category = "timeout"
            elif isinstance(error, EOFError):
                category = "eof"
            elif isinstance(error, OSError):
                errno = error.args[0] if error.args and type(error.args[0]) is int else None
                category = "os_error %d" % errno if errno is not None else "os_error"
            else:
                category = "invalid_response"
            log("delivery_error", category)
        return "retry", None
    if status in (200, 201) and headers.get("content-type", "").split(";")[0].strip().lower() != "application/json":
        return "retry", None
    action = response_action(status, response, body)
    if action == "ack":
        queue.ack(name, body)
    elif action == "quarantine":
        queue.quarantine(name)
    return action, headers.get("retry-after")


async def run(queue, sensor, device_id, transport, network_ready, clock, log=print):
    global _running
    if _running:
        raise RuntimeError("TLM runtime already running; reset device before manual restart")
    _running = True
    # The new stream affects only newly sampled packets, never the persisted queue.
    stream_id = uuid4()
    cadence = Cadence(clock.ticks_ms(), clock.ticks_add, clock.ticks_diff)
    sequence = 1
    attempt = 0
    try:
        while True:
            # A persisted message always wins. No later sensor read occurs until
            # it receives a valid ACK or is explicitly quarantined.
            if not queue.has_pending():
                if cadence.due(clock.ticks_ms()):
                    try:
                        sample_once(queue, sensor, device_id, stream_id, sequence)
                    except SensorReadError:
                        # Missing/out-of-range echoes are NOT converted into fake readings.
                        log("sensor_error: no valid distance; sample omitted")
                    else:
                        log("sample_persisted", sequence)
                        sequence += 1
                if not queue.has_pending():
                    await asyncio.sleep(0.05)
                    continue

            if not await network_ready():
                await asyncio.sleep(1)
                continue
            action, retry_after = await send_once(queue, transport, log)
            if action == "fatal":
                raise RuntimeError("Device authorization or endpoint needs operator attention")
            if action == "retry":
                delay = retry_seconds(attempt, retry_after)
                attempt = min(attempt + 1, 6)
                log("delivery_retry", delay)
                await asyncio.sleep(delay)
            else:
                attempt = 0
                if action != "empty":
                    log("delivery_" + action, queue.count())
                await asyncio.sleep(0.05)
    finally:
        _running = False
