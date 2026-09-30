from datetime import datetime, timedelta, timezone

import pytest

from tlm_device_data_platform.simulation import (
    FixtureExhaustedError,
    ManualClock,
    ScriptedTransport,
    SequenceSensor,
    TemporaryFileQueue,
)


TEST_READING_FIXTURES = ("test-reading-a", "test-reading-b")
TEST_START_TIME = datetime(2042, 1, 2, 3, 4, tzinfo=timezone.utc)
TEST_TIME_ADVANCE = timedelta(seconds=7)
TEST_DELIVERY_RESULTS = (False, True)
TEST_MESSAGES = (b"test-message-a", b"test-message-b")


def test_sequence_sensor_returns_configured_readings_in_order() -> None:
    sensor = SequenceSensor(TEST_READING_FIXTURES)

    assert sensor.read() == "test-reading-a"
    assert sensor.read() == "test-reading-b"
    with pytest.raises(FixtureExhaustedError, match="test reading"):
        sensor.read()


def test_manual_clock_changes_only_when_advanced() -> None:
    clock = ManualClock(TEST_START_TIME)

    assert clock.now() == TEST_START_TIME
    assert clock.now() == TEST_START_TIME

    clock.advance(TEST_TIME_ADVANCE)

    assert clock.now() == TEST_START_TIME + TEST_TIME_ADVANCE


def test_scripted_transport_records_attempts_and_configured_results() -> None:
    transport = ScriptedTransport(TEST_DELIVERY_RESULTS)

    assert transport.send(TEST_MESSAGES[0]) is False
    assert transport.send(TEST_MESSAGES[1]) is True
    assert transport.attempts == TEST_MESSAGES
    with pytest.raises(FixtureExhaustedError, match="delivery result"):
        transport.send(b"unconfigured-test-message")


def test_temporary_file_queue_persists_fifo_order_across_instances(tmp_path) -> None:
    queue_path = tmp_path / "test-queue.json"
    first_instance = TemporaryFileQueue(queue_path)

    first_instance.enqueue(TEST_MESSAGES[0])
    first_instance.enqueue(TEST_MESSAGES[1])

    second_instance = TemporaryFileQueue(queue_path)
    assert len(second_instance) == 2
    assert second_instance.peek() == TEST_MESSAGES[0]
    assert second_instance.peek() == TEST_MESSAGES[0]
    assert second_instance.dequeue() == TEST_MESSAGES[0]

    third_instance = TemporaryFileQueue(queue_path)
    assert len(third_instance) == 1
    assert third_instance.dequeue() == TEST_MESSAGES[1]
    assert third_instance.dequeue() is None
    assert len(third_instance) == 0
