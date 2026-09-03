from datetime import datetime

import pytest

from daisy_pet.custom_reminders import CustomReminder, CustomReminderStore


class FakeClock:
    def __init__(self, value=100.0):
        self.value = value

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
        from datetime import timedelta

        self.moment += timedelta(**kwargs)


def test_interval_mode_due_respects_enabled_flag():
    clock = FakeClock()
    item = CustomReminder(
        "id1", "Stretch", interval_minutes=1, enabled=False, monotonic_clock=clock
    )
    clock.advance(60)
    assert not item.due()  # disabled, even though the interval elapsed

    item.enabled = True
    assert item.due()


def test_interval_mode_mark_fired_resets_countdown():
    clock = FakeClock()
    item = CustomReminder("id1", "Stand up", interval_minutes=1, monotonic_clock=clock)
    clock.advance(60)
    assert item.due()
    item.mark_fired()
    assert not item.due()


def test_time_of_day_mode_due_and_mark_fired_rolls_to_next_day():
    wall = FakeWallClock(datetime(2024, 1, 1, 14, 59))
    item = CustomReminder(
        "id1", "Afternoon check-in", mode="time_of_day", time_of_day="15:00",
        wall_clock=wall,
    )
    assert not item.due()
    wall.advance(minutes=1)
    assert item.due()
    item.mark_fired()
    assert not item.due()
    assert item.seconds_remaining == pytest.approx(24 * 3600, rel=0.01)


def test_snooze_uses_reminders_own_snooze_minutes_by_default():
    clock = FakeClock()
    item = CustomReminder(
        "id1", "Stretch", interval_minutes=30, snooze_minutes=5, monotonic_clock=clock
    )
    clock.advance(30 * 60)
    assert item.due()
    item.snooze()
    assert not item.due()
    clock.advance(5 * 60 - 1)
    assert not item.due()
    clock.advance(1)
    assert item.due()


def test_snooze_accepts_explicit_override():
    clock = FakeClock()
    item = CustomReminder(
        "id1", "Stretch", interval_minutes=30, snooze_minutes=5, monotonic_clock=clock
    )
    item.snooze(20)
    clock.advance(20 * 60)
    assert item.due()


def test_custom_reminder_rejects_blank_text():
    with pytest.raises(ValueError):
        CustomReminder("id1", "   ", interval_minutes=10)


def test_custom_reminder_rejects_invalid_snooze_minutes():
    with pytest.raises(ValueError):
        CustomReminder("id1", "Stretch", interval_minutes=10, snooze_minutes=0)


def test_custom_reminder_requires_interval_minutes_in_interval_mode():
    with pytest.raises(ValueError):
        CustomReminder("id1", "Stretch", mode="interval")


def test_custom_reminder_requires_time_of_day_in_time_mode():
    with pytest.raises(ValueError):
        CustomReminder("id1", "Stretch", mode="time_of_day")


def test_custom_reminder_rejects_unknown_mode():
    with pytest.raises(ValueError):
        CustomReminder("id1", "Stretch", mode="whenever", interval_minutes=10)


def test_summary_text_for_each_mode():
    interval_item = CustomReminder("id1", "Stretch", interval_minutes=45)
    assert interval_item.summary() == "Stretch — every 45 min"

    time_item = CustomReminder(
        "id2", "Lunch", mode="time_of_day", time_of_day="13:00"
    )
    assert time_item.summary() == "Lunch — daily at 13:00"


def test_interval_mode_round_trips_through_dict():
    clock = FakeClock()
    item = CustomReminder(
        "id1",
        "Eat lunch",
        interval_minutes=90,
        snooze_minutes=15,
        enabled=False,
        monotonic_clock=clock,
    )
    data = item.to_dict()
    assert data == {
        "id": "id1",
        "text": "Eat lunch",
        "mode": "interval",
        "interval_minutes": 90,
        "time_of_day": None,
        "snooze_minutes": 15,
        "enabled": False,
    }
    restored = CustomReminder.from_dict(data, monotonic_clock=clock)
    assert restored.reminder_id == "id1"
    assert restored.mode == "interval"
    assert restored.interval_minutes == 90
    assert restored.snooze_minutes == 15
    assert restored.enabled is False


def test_time_of_day_mode_round_trips_through_dict():
    wall = FakeWallClock(datetime(2024, 1, 1, 10, 0))
    item = CustomReminder(
        "id2", "Afternoon check-in", mode="time_of_day", time_of_day="15:30",
        wall_clock=wall,
    )
    data = item.to_dict()
    assert data["mode"] == "time_of_day"
    assert data["time_of_day"] == "15:30"
    assert data["interval_minutes"] is None
    restored = CustomReminder.from_dict(data, wall_clock=wall)
    assert restored.mode == "time_of_day"
    assert restored.time_of_day == "15:30"


def test_from_dict_defaults_missing_mode_and_snooze_for_backward_compatibility():
    clock = FakeClock()
    old_shape = {"id": "id1", "text": "Stretch", "interval_minutes": 20, "enabled": True}
    restored = CustomReminder.from_dict(old_shape, monotonic_clock=clock)
    assert restored.mode == "interval"
    assert restored.snooze_minutes == 10


def test_store_add_remove_find_and_due_items():
    clock = FakeClock()
    store = CustomReminderStore()
    a = store.add("Stretch", interval_minutes=1, monotonic_clock=clock)
    b = store.add("Stand up", interval_minutes=2, monotonic_clock=clock)
    assert len(store.items) == 2
    assert store.find(a.reminder_id) is a
    assert store.find("nonexistent") is None

    clock.advance(60)
    assert store.due_items() == [a]

    clock.advance(60)
    assert store.due_items() == [a, b]

    store.remove(a.reminder_id)
    assert store.due_items() == [b]
    assert len(store.items) == 1


def test_store_config_list_round_trip():
    clock = FakeClock()
    store = CustomReminderStore()
    store.add("Stretch", interval_minutes=30, monotonic_clock=clock)
    store.add(
        "Stand up", interval_minutes=45, enabled=False, monotonic_clock=clock
    )

    data = store.to_config_list()
    restored = CustomReminderStore.from_config_list(data, monotonic_clock=clock)
    assert restored.to_config_list() == data
