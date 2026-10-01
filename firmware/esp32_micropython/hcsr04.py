"""HC-SR04 at 5 V; ECHO MUST pass through the documented voltage divider."""


class SensorReadError(Exception):
    pass


class HCSR04:
    def __init__(self, trigger_pin=26, echo_pin=27, pin_factory=None,
                 pulse_us=None, sleep_us=None):
        # This pilot is for a classic ESP32 DevKit; reject accidental flash/strap pins.
        allowed = (18, 19, 21, 22, 23, 25, 26, 27, 32, 33)
        if trigger_pin not in allowed or echo_pin not in allowed or trigger_pin == echo_pin:
            raise ValueError("Choose distinct supported DevKit GPIO pins")
        if pin_factory is None or pulse_us is None:
            import machine
            pin_factory = machine.Pin
            pulse_us = machine.time_pulse_us
        if sleep_us is None:
            from time import sleep_us
        self.trigger = pin_factory(trigger_pin, pin_factory.OUT, value=0)
        self.echo = pin_factory(echo_pin, pin_factory.IN)
        self.pulse_us = pulse_us
        self.sleep_us = sleep_us

    def read(self):
        if self.echo.value():
            raise SensorReadError("ECHO stuck high")
        self.trigger.value(0)
        self.sleep_us(2)
        self.trigger.value(1)
        self.sleep_us(10)
        self.trigger.value(0)
        duration = self.pulse_us(self.echo, 1, 30000)
        if duration <= 0:
            raise SensorReadError("No valid echo")
        distance = duration / 58.0  # HC-SR04 datasheet nominal conversion, cm.
        if not 2 <= distance <= 400:
            raise SensorReadError("Distance outside HC-SR04 specified range")
        return {"distance_cm": round(distance, 2)}
