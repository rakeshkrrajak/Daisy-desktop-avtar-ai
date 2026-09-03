import pytest

from daisy_pet.custom_reminders import CustomReminder, CustomReminderStore


class FakeClock:
    def __init__(self):
        self.value = 100.0

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


def test_custom_reminder_due_respects_enabled_flag():
    clock = FakeClock()
    item = CustomReminder("id1", "Stretch", 1, enabled=False, clock=clock)
    clock.advance(60)
    assert not item.due()  # disabled, even though the interval elapsed

    item.enabled = True
    assert item.due()


def test_custom_reminder_mark_fired_resets_countdown():
    clock = FakeClock()
    item = CustomReminder("id1", "Stand up", 1, clock=clock)
    clock.advance(60)
    assert item.due()
    item.mark_fired()
    assert not item.due()


def test_custom_reminder_rejects_blank_text():
    with pytest.raises(ValueError):
        CustomReminder("id1", "   ", 10)


def test_custom_reminder_round_trips_through_dict():
    clock = FakeClock()
    item = CustomReminder("id1", "Eat lunch", 90, enabled=False, clock=clock)
    data = item.to_dict()
    assert data == {
        "id": "id1",
        "text": "Eat lunch",
        "interval_minutes": 90,
        "enabled": False,
    }
    restored = CustomReminder.from_dict(data, clock=clock)
    assert restored.reminder_id == "id1"
    assert restored.text == "Eat lunch"
    assert restored.interval_minutes == 90
    assert restored.enabled is False


def test_store_add_remove_and_due_items():
    clock = FakeClock()
    store = CustomReminderStore()
    a = store.add("Stretch", 1, clock=clock)
    b = store.add("Stand up", 2, clock=clock)
    assert len(store.items) == 2

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
    store.add("Stretch", 30, clock=clock)
    store.add("Stand up", 45, enabled=False, clock=clock)

    data = store.to_config_list()
    restored = CustomReminderStore.from_config_list(data, clock=clock)
    assert restored.to_config_list() == data
