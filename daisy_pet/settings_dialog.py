from PySide6.QtCore import QTime, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QTimeEdit,
    QVBoxLayout,
)

from .config import MAX_CUSTOM_REMINDER_TEXT_LENGTH
from .custom_reminders import new_id


def _to_qtime(value: str) -> QTime:
    hours, minutes = value.split(":")
    return QTime(int(hours), int(minutes))


class AddCustomReminderDialog(QDialog):
    """Small popup for typing a new custom reminder's text and interval."""

    def __init__(self, parent: QDialog | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Reminder")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("e.g. Stretch, Stand up, Eat lunch")
        self.text_input.setMaxLength(MAX_CUSTOM_REMINDER_TEXT_LENGTH)

        self.interval_minutes = QSpinBox()
        self.interval_minutes.setRange(1, 1440)
        self.interval_minutes.setSuffix(" min")
        self.interval_minutes.setValue(30)

        form = QFormLayout()
        form.addRow("Reminder text", self.text_input)
        form.addRow("Every", self.interval_minutes)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self._on_accept)
        self.buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.buttons)

    def _on_accept(self) -> None:
        if self.text_input.text().strip():
            self.accept()

    def result_dict(self) -> dict:
        return {
            "id": new_id(),
            "text": self.text_input.text().strip(),
            "interval_minutes": self.interval_minutes.value(),
            "enabled": True,
        }


class SettingsDialog(QDialog):
    def __init__(self, cfg: dict, parent: QDialog | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Daisy Settings")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        self.interval_minutes = QSpinBox()
        self.interval_minutes.setRange(1, 240)
        self.interval_minutes.setSuffix(" min")
        self.interval_minutes.setValue(cfg["interval_minutes"])

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

        form = QFormLayout()
        form.addRow("Remind me to drink every", self.interval_minutes)
        form.addRow(self.walk_enabled)
        form.addRow("Act like drinking at", self.drink_fraction_percent)
        form.addRow("Wander every, at least", self.ambient_min)
        form.addRow("Wander every, at most", self.ambient_max)
        form.addRow("Seconds to cross the screen", self.crossing_seconds)
        form.addRow(self.schedule_enabled)
        form.addRow("Active from", self.schedule_start)
        form.addRow("Active until", self.schedule_end)

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
        item = QListWidgetItem(f"{data['text']} — every {data['interval_minutes']} min")
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
            "walk_enabled": self.walk_enabled.isChecked(),
            "walk_drink_fraction": self.drink_fraction_percent.value() / 100.0,
            "ambient_walk_min_minutes": ambient_min,
            "ambient_walk_max_minutes": ambient_max,
            "walk_crossing_seconds": self.crossing_seconds.value(),
            "schedule_enabled": self.schedule_enabled.isChecked(),
            "schedule_start": self.schedule_start.time().toString("HH:mm"),
            "schedule_end": self.schedule_end.time().toString("HH:mm"),
            "custom_reminders": self._custom_reminders(),
        }
