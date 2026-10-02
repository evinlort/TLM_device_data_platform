"""Explicit software-only example; never use these values as real measurements."""


def read() -> dict[str, float]:
    """Return visibly test-labeled values only when this module is selected."""
    return {"test_sensor_1": 21.5, "test_sensor_2": 48.0}
