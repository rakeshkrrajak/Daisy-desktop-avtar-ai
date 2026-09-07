from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog

from daisy_pet.config import DEFAULTS
from daisy_pet.settings_dialog import (
    AddCustomReminderDialog,
    AddNoteDialog,
    SettingsDialog,
)


def test_dialog_reflects_current_config(qapp):
    cfg = {
        **DEFAULTS,
        "interval_minutes": 5,
        "reminder_wait_seconds": 120,
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
        "tab_hints_enabled": True,
        "tab_review_enabled": True,
        "tab_idle_minutes": 60,
        "tab_min_open": 8,
        "liveliness_enabled": True,
        "liveliness_min_seconds": 45,
        "liveliness_max_seconds": 150,
        "memory_enabled": True,
        "summary_enabled": True,
        "summary_time": "18:00",
        "memory_retention_days": 30,
        "scale": 1.5,
    }
    dialog = SettingsDialog(cfg)
    assert dialog.reminder_wait_seconds.value() == 120
    dialog.reminder_wait_seconds.setValue(240)
    dialog.scale.setValue(2.1)
    dialog.activity_enabled.setChecked(False)
    dialog.tab_hints_enabled.setChecked(False)
    dialog.tab_review_enabled.setChecked(False)
    dialog.tab_idle_minutes.setValue(75)
    dialog.tab_min_open.setValue(10)
    dialog.liveliness_enabled.setChecked(False)
    dialog.liveliness_min_seconds.setValue(30)
    dialog.liveliness_max_seconds.setValue(120)
    dialog.memory_retention_days.setValue(14)
    assert dialog.values() == {
        "interval_minutes": 5,
        "reminder_wait_seconds": 240,
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
        "tab_hints_enabled": False,
        "tab_review_enabled": False,
        "tab_idle_minutes": 75,
        "tab_min_open": 10,
        "liveliness_enabled": False,
        "liveliness_min_seconds": 30,
        "liveliness_max_seconds": 120,
        "memory_enabled": True,
        "summary_enabled": True,
        "summary_time": "18:00",
        "memory_retention_days": 14,
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


def test_memory_controls_reflect_config_and_values(qapp):
    cfg = {
        **DEFAULTS,
        "memory_enabled": False,
        "summary_enabled": False,
        "summary_time": "20:30",
        "memory_retention_days": 7,
    }
    dialog = SettingsDialog(cfg)
    assert not dialog.memory_enabled.isChecked()
    assert not dialog.summary_enabled.isChecked()
    assert dialog.summary_time.time().toString("HH:mm") == "20:30"
    assert dialog.memory_retention_days.value() == 7

    dialog.memory_enabled.setChecked(True)
    dialog.summary_enabled.setChecked(True)
    values = dialog.values()
    assert values["memory_enabled"] is True
    assert values["summary_enabled"] is True
    assert values["summary_time"] == "20:30"
    assert values["memory_retention_days"] == 7


def test_note_dialog_returns_text_and_optional_due_date(qapp):
    from PySide6.QtCore import QDate

    dialog = AddNoteDialog()
    dialog.text_input.setText("  call Manisha  ")
    assert dialog.note_text() == "call Manisha"
    assert dialog.due_date_string() is None
    assert not dialog.due_date.isEnabled()

    dialog.due_enabled.setChecked(True)
    dialog.due_date.setDate(QDate(2026, 3, 4))
    assert dialog.due_date.isEnabled()
    assert dialog.due_date_string() == "2026-03-04"


def test_note_dialog_rejects_blank_text(qapp):
    dialog = AddNoteDialog()
    dialog.text_input.setText("   ")
    dialog._on_accept()
    assert dialog.result() != QDialog.Accepted


def test_add_dialog_rejects_blank_text(qapp):
    add_dialog = AddCustomReminderDialog()
    add_dialog.text_input.setText("   ")
    add_dialog._on_accept()
    assert add_dialog.result() != QDialog.Accepted
