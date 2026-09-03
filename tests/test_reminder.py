import random
from datetime import datetime, timedelta

import pytest

from daisy_pet.reminder import TimeOfDayReminder, WaterReminder, pick_message


class FakeClock:
    def __init__(self):
        self.value = 100.0

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


class FakeWallClock:
    def __init__(self, moment: datetime):
        self.moment = moment

    def __call__(self) -> datetime:
        return self.moment

    def advance(self, **kwargs):
        self.moment += timedelta(**kwargs)


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


def test_time_of_day_reminder_fires_at_target_and_rolls_to_tomorrow():
    wall = FakeWallClock(datetime(2024, 6, 1, 14, 59, 30))
    reminder = TimeOfDayReminder("15:00", wall)
    assert not reminder.due()
    wall.advance(seconds=30)
    assert reminder.due()
    reminder.mark_fired()
    assert not reminder.due()
    assert reminder.seconds_remaining == pytest.approx(24 * 3600, abs=1)


def test_time_of_day_reminder_schedules_for_tomorrow_if_time_already_passed():
    wall = FakeWallClock(datetime(2024, 6, 1, 20, 0, 0))
    reminder = TimeOfDayReminder("15:00", wall)
    assert not reminder.due()
    wall.advance(hours=19)  # now 15:00 the next day
    assert reminder.due()


def test_time_of_day_reminder_snooze_and_set_time_of_day():
    wall = FakeWallClock(datetime(2024, 6, 1, 15, 0, 0))
    reminder = TimeOfDayReminder("15:00", wall)
    reminder.snooze(10)
    assert reminder.seconds_remaining == pytest.approx(600)

    reminder.set_time_of_day("09:00")
    assert reminder.time_of_day == "09:00"
    assert not reminder.due()  # 09:00 already passed today, rolled to tomorrow


def test_time_of_day_reminder_rejects_invalid_time_string():
    with pytest.raises(ValueError):
        TimeOfDayReminder("25:99")


def test_time_of_day_reminder_snooze_validates_minutes():
    reminder = TimeOfDayReminder("15:00", FakeWallClock(datetime(2024, 6, 1, 10, 0)))
    with pytest.raises(ValueError):
        reminder.snooze(0)
