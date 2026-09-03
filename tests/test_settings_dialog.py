from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog

from daisy_pet.config import DEFAULTS
from daisy_pet.settings_dialog import AddCustomReminderDialog, SettingsDialog


def test_dialog_reflects_current_config(qapp):
    cfg = {
        **DEFAULTS,
        "interval_minutes": 5,
        "walk_enabled": False,
        "walk_drink_fraction": 0.4,
        "ambient_walk_min_minutes": 4,
        "ambient_walk_max_minutes": 9,
        "walk_crossing_seconds": 11,
        "schedule_enabled": True,
        "schedule_start": "09:15",
        "schedule_end": "17:45",
        "custom_reminders": [],
        "mood_enabled": True,
        "ollama_enabled": False,
        "ollama_url": "http://127.0.0.1:11434",
        "ollama_model": "llama3.2",
        "activity_enabled": True,
        "scale": 1.5,
    }
    dialog = SettingsDialog(cfg)
    dialog.scale.setValue(2.1)
    dialog.activity_enabled.setChecked(False)
    assert dialog.values() == {
        "interval_minutes": 5,
        "scale": 2.1,
        "walk_enabled": False,
        "walk_drink_fraction": 0.4,
        "ambient_walk_min_minutes": 4,
        "ambient_walk_max_minutes": 9,
        "walk_crossing_seconds": 11,
        "schedule_enabled": True,
        "schedule_start": "09:15",
        "schedule_end": "17:45",
        "custom_reminders": [],
        "mood_enabled": True,
        "ollama_enabled": False,
        "ollama_url": "http://127.0.0.1:11434",
        "ollama_model": "llama3.2",
        "activity_enabled": False,
    }


def test_dialog_clamps_max_to_min(qapp):
    cfg = {**DEFAULTS, "ambient_walk_min_minutes": 10, "ambient_walk_max_minutes": 5}
    dialog = SettingsDialog(cfg)
    dialog.ambient_min.setValue(10)
    dialog.ambient_max.setValue(5)
    assert dialog.values()["ambient_walk_max_minutes"] == 10


def test_dialog_preloads_existing_custom_reminders(qapp):
    cfg = {
        **DEFAULTS,
        "custom_reminders": [
            {"id": "a1", "text": "Stretch", "interval_minutes": 45, "enabled": True},
            {"id": "b2", "text": "Stand up", "interval_minutes": 20, "enabled": False},
            {
                "id": "c3",
                "text": "Lunch",
                "mode": "time_of_day",
                "time_of_day": "13:00",
                "snooze_minutes": 5,
                "enabled": True,
            },
        ],
    }
    dialog = SettingsDialog(cfg)
    assert dialog.custom_list.count() == 3
    assert dialog.custom_list.item(2).text() == "Lunch — daily at 13:00"
    assert dialog.values()["custom_reminders"] == cfg["custom_reminders"]


def test_add_and_remove_custom_reminder_via_dialog(qapp):
    cfg = {**DEFAULTS}
    dialog = SettingsDialog(cfg)
    assert dialog.custom_list.count() == 0

    add_dialog = AddCustomReminderDialog()
    add_dialog.text_input.setText("Eat lunch")
    add_dialog.interval_minutes.setValue(90)
    data = add_dialog.result_dict()
    assert data["text"] == "Eat lunch"
    assert data["mode"] == "interval"
    assert data["interval_minutes"] == 90
    assert data["time_of_day"] is None
    assert data["snooze_minutes"] == 10
    assert data["enabled"] is True
    assert data["id"]

    dialog._add_list_item(data)
    assert dialog.custom_list.count() == 1
    saved = dialog.values()["custom_reminders"]
    assert len(saved) == 1
    assert saved[0]["text"] == "Eat lunch"

    dialog.custom_list.item(0).setSelected(True)
    dialog._on_remove_selected()
    assert dialog.custom_list.count() == 0
    assert dialog.values()["custom_reminders"] == []


def test_add_dialog_time_of_day_mode(qapp):
    from PySide6.QtCore import QTime

    add_dialog = AddCustomReminderDialog()
    add_dialog.text_input.setText("Afternoon check-in")
    add_dialog.time_of_day_radio.setChecked(True)
    add_dialog.time_of_day.setTime(QTime(15, 30))
    add_dialog.snooze_minutes.setValue(5)

    assert not add_dialog.interval_minutes.isEnabled()
    assert add_dialog.time_of_day.isEnabled()

    data = add_dialog.result_dict()
    assert data["mode"] == "time_of_day"
    assert data["time_of_day"] == "15:30"
    assert data["interval_minutes"] is None
    assert data["snooze_minutes"] == 5


def test_add_dialog_defaults_to_interval_mode_enabled_fields(qapp):
    add_dialog = AddCustomReminderDialog()
    assert add_dialog.interval_radio.isChecked()
    assert add_dialog.interval_minutes.isEnabled()
    assert not add_dialog.time_of_day.isEnabled()


def test_unchecking_custom_reminder_item_disables_it(qapp):
    cfg = {
        **DEFAULTS,
        "custom_reminders": [
            {"id": "a1", "text": "Stretch", "interval_minutes": 45, "enabled": True},
        ],
    }
    dialog = SettingsDialog(cfg)
    item = dialog.custom_list.item(0)
    item.setCheckState(Qt.Unchecked)
    assert dialog.values()["custom_reminders"][0]["enabled"] is False


def test_add_dialog_rejects_blank_text(qapp):
    add_dialog = AddCustomReminderDialog()
    add_dialog.text_input.setText("   ")
    add_dialog._on_accept()
    assert add_dialog.result() != QDialog.Accepted
