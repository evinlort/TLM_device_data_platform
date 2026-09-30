from pathlib import Path

from tlm_device_data_platform.simulation import (
    ScriptedTransport,
    TemporaryFileQueue,
    flush_test_queue,
)
from tlm_device_data_platform.telemetry_fixture import (
    FIXTURE_SCHEMA_VERSION,
    TelemetryFixtureEnvelope,
    parse_fixture_telemetry,
    serialize_fixture_telemetry,
)


TEST_STREAM_ID = "test-step-5-stream"
TEST_RECORDED_AT = "2042-01-02T03:04:05Z"
TEST_CORRECTNESS_BURST_SIZE = 64


def _test_envelope(
    sequence_no: int,
    *,
    message_id: str | None = None,
) -> TelemetryFixtureEnvelope:
    return TelemetryFixtureEnvelope(
        schema_version=FIXTURE_SCHEMA_VERSION,
        message_id=message_id or f"test-step-5-message-{sequence_no}",
        stream_id=TEST_STREAM_ID,
        sequence_no=sequence_no,
        recorded_at=TEST_RECORDED_AT,
        payload={"test_reading": sequence_no * 10},
    )


def _logical_fixture_acceptance(
    messages: tuple[bytes, ...],
) -> tuple[TelemetryFixtureEnvelope, ...]:
    """Accept the first occurrence of each fixture message_id for this test only."""
    accepted_by_message_id: dict[str, TelemetryFixtureEnvelope] = {}
    for message in messages:
        envelope = parse_fixture_telemetry(message)
        accepted_by_message_id.setdefault(envelope.message_id, envelope)
    return tuple(accepted_by_message_id.values())


def _enqueue(queue_path: Path, messages: tuple[bytes, ...]) -> None:
    queue = TemporaryFileQueue(queue_path)
    for message in messages:
        queue.enqueue(message)


def test_duplicate_message_id_retry_is_logically_accepted_once(tmp_path) -> None:
    queue_path = tmp_path / "duplicate-test-queue.json"
    envelope = _test_envelope(1, message_id="test-duplicate-message")
    message = serialize_fixture_telemetry(envelope)
    _enqueue(queue_path, (message, message))
    transport = ScriptedTransport((True, True))

    delivered = flush_test_queue(TemporaryFileQueue(queue_path), transport)
    accepted = _logical_fixture_acceptance(delivered)

    assert transport.attempts == (message, message)
    assert delivered == (message, message)
    assert accepted == (envelope,)
    assert len(TemporaryFileQueue(queue_path)) == 0


def test_unavailable_transport_retains_messages_in_test_queue(tmp_path) -> None:
    queue_path = tmp_path / "offline-test-queue.json"
    messages = tuple(
        serialize_fixture_telemetry(_test_envelope(sequence_no))
        for sequence_no in (1, 2)
    )
    _enqueue(queue_path, messages)
    unavailable_transport = ScriptedTransport((False,))

    delivered = flush_test_queue(
        TemporaryFileQueue(queue_path),
        unavailable_transport,
    )

    persisted_queue = TemporaryFileQueue(queue_path)
    assert delivered == ()
    assert unavailable_transport.attempts == (messages[0],)
    assert len(persisted_queue) == 2
    assert persisted_queue.dequeue() == messages[0]
    assert persisted_queue.dequeue() == messages[1]


def test_reconnect_replays_persisted_messages_in_fifo_order(tmp_path) -> None:
    queue_path = tmp_path / "reconnect-test-queue.json"
    messages = tuple(
        serialize_fixture_telemetry(_test_envelope(sequence_no))
        for sequence_no in (1, 2, 3)
    )
    _enqueue(queue_path, messages)

    unavailable_transport = ScriptedTransport((False,))
    assert (
        flush_test_queue(TemporaryFileQueue(queue_path), unavailable_transport) == ()
    )

    reconnected_transport = ScriptedTransport((True, True, True))
    replayed = flush_test_queue(
        TemporaryFileQueue(queue_path),
        reconnected_transport,
    )
    replayed_envelopes = tuple(parse_fixture_telemetry(item) for item in replayed)

    assert reconnected_transport.attempts == messages
    assert tuple(item.sequence_no for item in replayed_envelopes) == (1, 2, 3)
    assert len(TemporaryFileQueue(queue_path)) == 0


def test_reconnect_replays_correctness_scale_buffered_burst(tmp_path) -> None:
    queue_path = tmp_path / "burst-test-queue.json"
    messages = tuple(
        serialize_fixture_telemetry(_test_envelope(sequence_no))
        for sequence_no in range(1, TEST_CORRECTNESS_BURST_SIZE + 1)
    )
    _enqueue(queue_path, messages)

    unavailable_transport = ScriptedTransport((False,))
    assert (
        flush_test_queue(TemporaryFileQueue(queue_path), unavailable_transport) == ()
    )
    assert len(TemporaryFileQueue(queue_path)) == TEST_CORRECTNESS_BURST_SIZE

    reconnected_transport = ScriptedTransport(
        (True,) * TEST_CORRECTNESS_BURST_SIZE
    )
    replayed = flush_test_queue(
        TemporaryFileQueue(queue_path),
        reconnected_transport,
    )
    replayed_sequence = tuple(
        parse_fixture_telemetry(message).sequence_no for message in replayed
    )

    assert replayed == messages
    assert replayed_sequence == tuple(range(1, TEST_CORRECTNESS_BURST_SIZE + 1))
    assert len(TemporaryFileQueue(queue_path)) == 0
