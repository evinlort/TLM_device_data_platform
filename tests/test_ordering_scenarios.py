from datetime import datetime, timedelta, timezone

from tlm_device_data_platform.simulation import ManualClock
from tlm_device_data_platform.telemetry_fixture import (
    FIXTURE_SCHEMA_VERSION,
    TelemetryFixtureEnvelope,
    TelemetryFixtureProjection,
    serialize_fixture_telemetry,
)


TEST_STREAM_BEFORE_REBOOT = "test-step-6-stream-before-reboot"
TEST_STREAM_AFTER_REBOOT = "test-step-6-stream-after-reboot"
TEST_OBSERVATION_START = datetime(2042, 1, 2, 3, 4, tzinfo=timezone.utc)
TEST_OBSERVATION_ADVANCE = timedelta(seconds=1)


def _test_envelope(
    sequence_no: int,
    *,
    stream_id: str = TEST_STREAM_BEFORE_REBOOT,
    recorded_at: str = "2042-01-02T03:04:05Z",
) -> TelemetryFixtureEnvelope:
    return TelemetryFixtureEnvelope(
        schema_version=FIXTURE_SCHEMA_VERSION,
        message_id=f"test-step-6-{stream_id}-{sequence_no}-{recorded_at}",
        stream_id=stream_id,
        sequence_no=sequence_no,
        recorded_at=recorded_at,
        payload={"test_reading": sequence_no * 10},
    )


def _observe(
    projection: TelemetryFixtureProjection,
    clock: ManualClock,
    envelope: TelemetryFixtureEnvelope,
) -> None:
    projection.observe(
        serialize_fixture_telemetry(envelope),
        observed_at=clock.now(),
    )
    clock.advance(TEST_OBSERVATION_ADVANCE)


def test_out_of_order_history_does_not_roll_back_fixture_current_state() -> None:
    clock = ManualClock(TEST_OBSERVATION_START)
    projection = TelemetryFixtureProjection(TEST_STREAM_BEFORE_REBOOT)
    envelopes = tuple(_test_envelope(sequence_no) for sequence_no in (1, 3, 2))

    for envelope in envelopes:
        _observe(projection, clock, envelope)

    assert tuple(
        item.envelope.sequence_no for item in projection.history
    ) == (1, 3, 2)
    assert tuple(item.observation_no for item in projection.history) == (1, 2, 3)
    assert projection.current_state == envelopes[1]


def test_new_fixture_stream_permits_sequence_restart_after_test_reboot() -> None:
    clock = ManualClock(TEST_OBSERVATION_START)
    projection = TelemetryFixtureProjection(TEST_STREAM_BEFORE_REBOOT)
    before_reboot = _test_envelope(41)
    after_reboot = _test_envelope(1, stream_id=TEST_STREAM_AFTER_REBOOT)

    _observe(projection, clock, before_reboot)
    projection.activate_test_stream(TEST_STREAM_AFTER_REBOOT)
    _observe(projection, clock, after_reboot)

    assert projection.active_stream_id == TEST_STREAM_AFTER_REBOOT
    assert tuple(
        (item.envelope.stream_id, item.envelope.sequence_no)
        for item in projection.history
    ) == (
        (TEST_STREAM_BEFORE_REBOOT, 41),
        (TEST_STREAM_AFTER_REBOOT, 1),
    )
    assert projection.current_state == after_reboot


def test_late_fixture_telemetry_stays_in_history_without_replacing_new_stream() -> None:
    clock = ManualClock(TEST_OBSERVATION_START)
    projection = TelemetryFixtureProjection(TEST_STREAM_BEFORE_REBOOT)
    before_reboot = _test_envelope(41)
    after_reboot = _test_envelope(1, stream_id=TEST_STREAM_AFTER_REBOOT)
    late_before_reboot = _test_envelope(42)

    _observe(projection, clock, before_reboot)
    projection.activate_test_stream(TEST_STREAM_AFTER_REBOOT)
    _observe(projection, clock, after_reboot)
    _observe(projection, clock, late_before_reboot)

    assert tuple(
        (item.envelope.stream_id, item.envelope.sequence_no)
        for item in projection.history
    ) == (
        (TEST_STREAM_BEFORE_REBOOT, 41),
        (TEST_STREAM_AFTER_REBOOT, 1),
        (TEST_STREAM_BEFORE_REBOOT, 42),
    )
    assert projection.current_state == after_reboot


def test_device_clock_skew_cannot_choose_or_authorize_fixture_current_state() -> None:
    clock = ManualClock(TEST_OBSERVATION_START)
    projection = TelemetryFixtureProjection(TEST_STREAM_BEFORE_REBOOT)
    future_device_time = _test_envelope(1, recorded_at="2099-12-31T23:59:59Z")
    earlier_device_time = _test_envelope(2, recorded_at="2001-01-01T00:00:00Z")
    inactive_stream_future = _test_envelope(
        999,
        stream_id=TEST_STREAM_AFTER_REBOOT,
        recorded_at="2999-12-31T23:59:59Z",
    )

    _observe(projection, clock, future_device_time)
    _observe(projection, clock, earlier_device_time)
    _observe(projection, clock, inactive_stream_future)

    assert tuple(item.observed_at for item in projection.history) == (
        TEST_OBSERVATION_START,
        TEST_OBSERVATION_START + TEST_OBSERVATION_ADVANCE,
        TEST_OBSERVATION_START + (2 * TEST_OBSERVATION_ADVANCE),
    )
    assert tuple(item.envelope.recorded_at for item in projection.history) == (
        "2099-12-31T23:59:59Z",
        "2001-01-01T00:00:00Z",
        "2999-12-31T23:59:59Z",
    )
    assert projection.active_stream_id == TEST_STREAM_BEFORE_REBOOT
    assert projection.current_state == earlier_device_time
