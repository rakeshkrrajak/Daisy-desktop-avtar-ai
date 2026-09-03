import random

import pytest

from daisy_pet.reminder import WaterReminder, pick_message


class FakeClock:
    def __init__(self):
        self.value = 100.0

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


def test_due_and_mark_fired():
    clock = FakeClock()
    reminder = WaterReminder(1, clock)
    assert reminder.seconds_remaining == 60
    assert not reminder.due()
    clock.advance(60)
    assert reminder.due()
    reminder.mark_fired()
    assert not reminder.due()
    assert reminder.seconds_remaining == 60


def test_snooze_and_set_interval():
    clock = FakeClock()
    reminder = WaterReminder(30, clock)
    reminder.snooze(10)
    assert reminder.seconds_remaining == 600
    reminder.set_interval(45)
    assert reminder.interval_minutes == 45
    assert reminder.seconds_remaining == 2700


def test_minute_validation():
    with pytest.raises(ValueError):
        WaterReminder(0)
    reminder = WaterReminder(1)
    with pytest.raises(ValueError):
        reminder.snooze(0)
    with pytest.raises(ValueError):
        reminder.set_interval(-1)


def test_pick_message_is_deterministic_with_rng():
    first = pick_message(random.Random(3))
    assert first == pick_message(random.Random(3))
