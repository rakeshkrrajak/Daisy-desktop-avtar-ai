from PySide6.QtCore import QTime, Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTimeEdit,
    QVBoxLayout,
)

from .config import MAX_CUSTOM_REMINDER_TEXT_LENGTH
from .custom_reminders import (
    DEFAULT_SNOOZE_MINUTES,
    MODE_INTERVAL,
    MODE_TIME_OF_DAY,
    new_id,
)


def _to_qtime(value: str) -> QTime:
    hours, minutes = value.split(":")
    return QTime(int(hours), int(minutes))


def _summary_text(data: dict) -> str:
    if data.get("mode", MODE_INTERVAL) == MODE_TIME_OF_DAY and data.get("time_of_day"):
        return f"{data['text']} — daily at {data['time_of_day']}"
    return f"{data['text']} — every {data.get('interval_minutes', '?')} min"


class AddCustomReminderDialog(QDialog):
    """Small popup for defining a new custom reminder: its text, when it
    fires (repeating interval or a fixed clock time), and its snooze length.
    """

    def __init__(self, parent: QDialog | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Reminder")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("e.g. Stretch, Stand up, Eat lunch")
        self.text_input.setMaxLength(MAX_CUSTOM_REMINDER_TEXT_LENGTH)

        self.interval_radio = QRadioButton("Repeat every")
        self.time_of_day_radio = QRadioButton("At a specific time")
        self.interval_radio.setChecked(True)
        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.interval_radio)
        self.mode_group.addButton(self.time_of_day_radio)
        self.interval_radio.toggled.connect(self._on_mode_changed)

        self.interval_minutes = QSpinBox()
        self.interval_minutes.setRange(1, 1440)
        self.interval_minutes.setSuffix(" min")
        self.interval_minutes.setValue(30)

        self.time_of_day = QTimeEdit()
        self.time_of_day.setDisplayFormat("HH:mm")
        self.time_of_day.setTime(QTime(15, 0))

        self.snooze_minutes = QSpinBox()
        self.snooze_minutes.setRange(1, 240)
        self.snooze_minutes.setSuffix(" min")
        self.snooze_minutes.setValue(DEFAULT_SNOOZE_MINUTES)

        form = QFormLayout()
        form.addRow("Reminder text", self.text_input)
        form.addRow(self.interval_radio, self.interval_minutes)
        form.addRow(self.time_of_day_radio, self.time_of_day)
        form.addRow("Snooze by", self.snooze_minutes)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self._on_accept)
        self.buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.buttons)

        self._on_mode_changed()

    def _on_mode_changed(self) -> None:
        use_interval = self.interval_radio.isChecked()
        self.interval_minutes.setEnabled(use_interval)
        self.time_of_day.setEnabled(not use_interval)

    def _on_accept(self) -> None:
        if self.text_input.text().strip():
            self.accept()

    def result_dict(self) -> dict:
        data = {
            "id": new_id(),
            "text": self.text_input.text().strip(),
            "snooze_minutes": self.snooze_minutes.value(),
            "enabled": True,
        }
        if self.interval_radio.isChecked():
            data["mode"] = MODE_INTERVAL
            data["interval_minutes"] = self.interval_minutes.value()
            data["time_of_day"] = None
        else:
            data["mode"] = MODE_TIME_OF_DAY
            data["time_of_day"] = self.time_of_day.time().toString("HH:mm")
            data["interval_minutes"] = None
        return data


class SettingsDialog(QDialog):
    def __init__(self, cfg: dict, parent: QDialog | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Daisy Settings")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        self.interval_minutes = QSpinBox()
        self.interval_minutes.setRange(1, 240)
        self.interval_minutes.setSuffix(" min")
        self.interval_minutes.setValue(cfg["interval_minutes"])

        self.reminder_wait_seconds = QSpinBox()
        self.reminder_wait_seconds.setRange(15, 600)
        self.reminder_wait_seconds.setSuffix(" sec")
        self.reminder_wait_seconds.setValue(cfg["reminder_wait_seconds"])

        self.scale = QDoubleSpinBox()
        self.scale.setRange(0.5, 3.0)
        self.scale.setSingleStep(0.1)
        self.scale.setDecimals(1)
        self.scale.setSuffix("×")
        self.scale.setValue(cfg["scale"])

        self.walk_enabled = QCheckBox("Enable walking animations")
        self.walk_enabled.setChecked(cfg["walk_enabled"])

        self.drink_fraction_percent = QSpinBox()
        self.drink_fraction_percent.setRange(5, 95)
        self.drink_fraction_percent.setSingleStep(5)
        self.drink_fraction_percent.setSuffix(" %")
        self.drink_fraction_percent.setValue(round(cfg["walk_drink_fraction"] * 100))

        self.ambient_min = QSpinBox()
        self.ambient_min.setRange(1, 240)
        self.ambient_min.setSuffix(" min")
        self.ambient_min.setValue(cfg["ambient_walk_min_minutes"])

        self.ambient_max = QSpinBox()
        self.ambient_max.setRange(1, 240)
        self.ambient_max.setSuffix(" min")
        self.ambient_max.setValue(cfg["ambient_walk_max_minutes"])

        self.crossing_seconds = QSpinBox()
        self.crossing_seconds.setRange(2, 60)
        self.crossing_seconds.setSuffix(" sec")
        self.crossing_seconds.setValue(cfg["walk_crossing_seconds"])

        self.schedule_enabled = QCheckBox("Restrict Daisy to active hours")
        self.schedule_enabled.setChecked(cfg["schedule_enabled"])

        self.schedule_start = QTimeEdit()
        self.schedule_start.setDisplayFormat("HH:mm")
        self.schedule_start.setTime(_to_qtime(cfg["schedule_start"]))

        self.schedule_end = QTimeEdit()
        self.schedule_end.setDisplayFormat("HH:mm")
        self.schedule_end.setTime(_to_qtime(cfg["schedule_end"]))

        self.mood_enabled = QCheckBox("Enable mood expressions")
        self.mood_enabled.setChecked(cfg["mood_enabled"])
        self.ollama_enabled = QCheckBox("Enable optional local Ollama lines")
        self.ollama_enabled.setChecked(cfg["ollama_enabled"])
        self.ollama_url = QLineEdit(cfg["ollama_url"])
        self.ollama_model = QLineEdit(cfg["ollama_model"])
        self.activity_enabled = QCheckBox("Enable activity awareness")
        self.activity_enabled.setChecked(cfg["activity_enabled"])
        self.tab_hints_enabled = QCheckBox("Suggest closing stale browser tabs")
        self.tab_hints_enabled.setChecked(cfg["tab_hints_enabled"])
        self.tab_review_enabled = QCheckBox("Walk me through stale tabs")
        self.tab_review_enabled.setChecked(cfg["tab_review_enabled"])
        self.tab_idle_minutes = QSpinBox()
        self.tab_idle_minutes.setRange(5, 1440)
        self.tab_idle_minutes.setSuffix(" min")
        self.tab_idle_minutes.setValue(cfg["tab_idle_minutes"])
        self.tab_min_open = QSpinBox()
        self.tab_min_open.setRange(1, 100)
        self.tab_min_open.setSuffix(" windows")
        self.tab_min_open.setValue(cfg["tab_min_open"])
        self.liveliness_enabled = QCheckBox("Enable lifelike idle behaviour")
        self.liveliness_enabled.setChecked(cfg["liveliness_enabled"])
        self.liveliness_min_seconds = QSpinBox()
        self.liveliness_min_seconds.setRange(10, 3600)
        self.liveliness_min_seconds.setSuffix(" sec")
        self.liveliness_min_seconds.setValue(cfg["liveliness_min_seconds"])
        self.liveliness_max_seconds = QSpinBox()
        self.liveliness_max_seconds.setRange(10, 3600)
        self.liveliness_max_seconds.setSuffix(" sec")
        self.liveliness_max_seconds.setValue(cfg["liveliness_max_seconds"])

        form = QFormLayout()
        form.addRow("Remind me to drink every", self.interval_minutes)
        form.addRow("Wait for my answer (seconds)", self.reminder_wait_seconds)
        form.addRow("Daisy size", self.scale)
        form.addRow(self.walk_enabled)
        form.addRow("Act like drinking at", self.drink_fraction_percent)
        form.addRow("Wander every, at least", self.ambient_min)
        form.addRow("Wander every, at most", self.ambient_max)
        form.addRow("Seconds to cross the screen", self.crossing_seconds)
        form.addRow(self.schedule_enabled)
        form.addRow("Active from", self.schedule_start)
        form.addRow("Active until", self.schedule_end)
        form.addRow(self.mood_enabled)
        form.addRow(self.ollama_enabled)
        form.addRow("Ollama URL", self.ollama_url)
        form.addRow("Ollama model", self.ollama_model)
        form.addRow(self.activity_enabled)
        form.addRow(self.tab_hints_enabled)
        form.addRow(self.tab_review_enabled)
        form.addRow("Stale tab age", self.tab_idle_minutes)
        form.addRow("Minimum browser windows", self.tab_min_open)
        form.addRow(self.liveliness_enabled)
        form.addRow("Idle pose at least every", self.liveliness_min_seconds)
        form.addRow("Idle pose at most every", self.liveliness_max_seconds)

        self.custom_list = QListWidget()
        for item in cfg["custom_reminders"]:
            self._add_list_item(item)

        add_button = QPushButton("Add...")
        add_button.clicked.connect(self._on_add_custom_reminder)
        remove_button = QPushButton("Remove selected")
        remove_button.clicked.connect(self._on_remove_selected)

        custom_buttons = QHBoxLayout()
        custom_buttons.addWidget(add_button)
        custom_buttons.addWidget(remove_button)
        custom_buttons.addStretch(1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(QLabel("Custom reminders (checked = enabled)"))
        layout.addWidget(self.custom_list)
        layout.addLayout(custom_buttons)
        layout.addWidget(buttons)

    def _add_list_item(self, data: dict) -> None:
        item = QListWidgetItem(_summary_text(data))
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Checked if data.get("enabled", True) else Qt.Unchecked)
        item.setData(Qt.UserRole, dict(data))
        self.custom_list.addItem(item)

    def _on_add_custom_reminder(self) -> None:
        dialog = AddCustomReminderDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self._add_list_item(dialog.result_dict())

    def _on_remove_selected(self) -> None:
        for item in self.custom_list.selectedItems():
            self.custom_list.takeItem(self.custom_list.row(item))

    def _custom_reminders(self) -> list[dict]:
        result = []
        for row in range(self.custom_list.count()):
            item = self.custom_list.item(row)
            data = dict(item.data(Qt.UserRole))
            data["enabled"] = item.checkState() == Qt.Checked
            result.append(data)
        return result

    def values(self) -> dict:
        ambient_min = self.ambient_min.value()
        ambient_max = max(ambient_min, self.ambient_max.value())
        return {
            "interval_minutes": self.interval_minutes.value(),
            "reminder_wait_seconds": self.reminder_wait_seconds.value(),
            "scale": self.scale.value(),
            "walk_enabled": self.walk_enabled.isChecked(),
            "walk_drink_fraction": self.drink_fraction_percent.value() / 100.0,
            "ambient_walk_min_minutes": ambient_min,
            "ambient_walk_max_minutes": ambient_max,
            "walk_crossing_seconds": self.crossing_seconds.value(),
            "schedule_enabled": self.schedule_enabled.isChecked(),
            "schedule_start": self.schedule_start.time().toString("HH:mm"),
            "schedule_end": self.schedule_end.time().toString("HH:mm"),
            "custom_reminders": self._custom_reminders(),
            "mood_enabled": self.mood_enabled.isChecked(),
            "ollama_enabled": self.ollama_enabled.isChecked(),
            "ollama_url": self.ollama_url.text().strip(),
            "ollama_model": self.ollama_model.text().strip(),
            "activity_enabled": self.activity_enabled.isChecked(),
            "tab_hints_enabled": self.tab_hints_enabled.isChecked(),
            "tab_review_enabled": self.tab_review_enabled.isChecked(),
            "tab_idle_minutes": self.tab_idle_minutes.value(),
            "tab_min_open": self.tab_min_open.value(),
            "liveliness_enabled": self.liveliness_enabled.isChecked(),
            "liveliness_min_seconds": self.liveliness_min_seconds.value(),
            "liveliness_max_seconds": max(
                self.liveliness_min_seconds.value(),
                self.liveliness_max_seconds.value(),
            ),
        }
