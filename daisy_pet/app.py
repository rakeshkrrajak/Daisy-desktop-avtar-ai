import random
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication, QDialog

from . import config, schedule
from .bubble import SpeechBubble
from .custom_reminders import CustomReminder, CustomReminderStore
from .pet_window import PetWindow
from .reminder import WaterReminder, pick_message
from .settings_dialog import SettingsDialog
from .sprites import SpriteSheet
from .tray import DaisyTray
from .walker import Walker


class DaisyApplication:
    def __init__(self, qt_app: QApplication) -> None:
        self.qt_app = qt_app
        self.cfg = config.load()
        sheet_path = Path(__file__).parent / "assets" / "spritesheet.webp"
        self.sprites = SpriteSheet(sheet_path, self.cfg["scale"])
        self.pet = PetWindow(self.sprites)
        self.pet.place_initial(self.cfg["pos"])
        self.bubble = SpeechBubble()
        self.reminder = WaterReminder(self.cfg["interval_minutes"])
        self.custom_reminders = CustomReminderStore.from_config_list(
            self.cfg["custom_reminders"]
        )
        self.walker = Walker(self.pet)
        self.pet.moved.connect(self._save_position)
        self.pet.clicked.connect(self._show_next_reminder)
        self.pet.right_clicked.connect(self._open_pet_menu)
        self.pet.double_clicked.connect(self._vanish_now)
        self.tray = DaisyTray(
            self.sprites.frames("idle")[0],
            drink_now=self.drink_now,
            snooze=self.snooze,
            set_interval=self.set_interval,
            set_enabled=self.set_enabled,
            quit_app=self.qt_app.quit,
            open_settings=self.open_settings,
            interval=self.reminder.interval_minutes,
            enabled=self.cfg["enabled"],
        )
        self._schedule_hidden = False
        self.tray.show()
        if self._schedule_active():
            self.pet.show()
        else:
            self._schedule_hidden = True
        self.poll_timer = QTimer()
        self.poll_timer.setInterval(1000)
        self.poll_timer.timeout.connect(self._poll_reminder)
        self.poll_timer.start()
        self.ambient_timer = QTimer()
        self.ambient_timer.setSingleShot(True)
        self.ambient_timer.timeout.connect(self._on_ambient_timer)
        self._schedule_next_ambient_walk()

    def _save_position(self, position) -> None:
        self.cfg["pos"] = [position.x(), position.y()]
        config.save(self.cfg)

    def _show_message(self, text: str) -> None:
        self.bubble.show_message(text, self.pet.geometry(), self.cfg["bubble_seconds"])

    def _open_pet_menu(self) -> None:
        self.tray.menu.popup(QCursor.pos())

    def _show_next_reminder(self) -> None:
        if not self.cfg["enabled"]:
            self._show_message(
                "Reminders are paused — wake me from the tray menu."
            )
            return
        minutes = max(0, round(self.reminder.seconds_remaining / 60))
        self._show_message(f"Next sip in ~{minutes} min")

    def _vanish_now(self) -> None:
        """Double-click Daisy to instantly dismiss her, whatever she's doing —
        idle, mid-walk, or mid-reminder. She reappears at the next reminder
        (or ambient wander) like she normally would after one finishes.
        """
        self.bubble.hide()
        self.pet.stop_walk()
        self.pet.stop_sip()
        self.walker.busy = False
        self.pet.hide()

    def _schedule_active(self) -> bool:
        if not self.cfg["schedule_enabled"]:
            return True
        return schedule.is_active(self.cfg["schedule_start"], self.cfg["schedule_end"])

    def _apply_schedule_visibility(self) -> None:
        """Hide/show Daisy for active-hours only; leaves alone the separate
        hidden-until-next-reminder state she's in between walk-in cycles.
        """
        if self.walker.busy:
            return
        if not self._schedule_active():
            if self.pet.isVisible():
                self.pet.hide()
                self.bubble.hide()
            self._schedule_hidden = True
        elif self._schedule_hidden:
            self.pet.show()
            self._schedule_hidden = False

    def _poll_reminder(self) -> None:
        self._apply_schedule_visibility()
        if not self.cfg["enabled"] or self.walker.busy or not self._schedule_active():
            return
        if self.reminder.due():
            if self.cfg["walk_enabled"]:
                self._start_water_reminder_walk()
            else:
                self.drink_now(mark=True)
            return
        for item in self.custom_reminders.due_items():
            if self.cfg["walk_enabled"]:
                self._start_custom_reminder_walk(item)
            else:
                self._announce_custom_reminder(item)
            return  # one reminder event per tick keeps the walk cycle exclusive

    def _start_reminder_walk(self, message: str, act_it_out) -> None:
        """Shared walk-in/pause/walk-out cinematic for any reminder kind.

        `act_it_out` plays whatever pose fits (drinking, waving, ...) and
        marks the specific reminder as fired; the message bubble and the
        walk choreography around it are the same either way.
        """
        crossing = self.cfg["walk_crossing_seconds"]
        fraction = self.cfg["walk_drink_fraction"]

        def at_point() -> None:
            act_it_out()
            self._show_message(message)
            QTimer.singleShot(
                max(1, self.cfg["bubble_seconds"]) * 1000, self._finish_reminder_walk
            )

        self.walker.reminder_walk_in(crossing, fraction, at_point)

    def _finish_reminder_walk(self) -> None:
        if not self.pet.isVisible():
            return  # already dismissed (e.g. double-click vanish) — nothing to finish
        self.walker.reminder_walk_out(self.cfg["walk_crossing_seconds"], self.pet.hide)

    def _start_water_reminder_walk(self) -> None:
        def act_it_out() -> None:
            self.pet.start_sip()
            self.reminder.mark_fired()

        self._start_reminder_walk(f"💧 {pick_message()}", act_it_out)

    def _start_custom_reminder_walk(self, item: CustomReminder) -> None:
        def act_it_out() -> None:
            self.pet.play("waving", loops=2, then="idle")
            item.mark_fired()

        self._start_reminder_walk(f"🔔 {item.text}", act_it_out)

    def _announce_custom_reminder(self, item: CustomReminder) -> None:
        if not self.pet.isVisible():
            self.pet.show()
        self.pet.play("waving", loops=2)
        self._show_message(f"🔔 {item.text}")
        item.mark_fired()

    def _schedule_next_ambient_walk(self) -> None:
        minutes = random.uniform(
            self.cfg["ambient_walk_min_minutes"], self.cfg["ambient_walk_max_minutes"]
        )
        self.ambient_timer.start(max(1000, int(minutes * 60 * 1000)))

    def _on_ambient_timer(self) -> None:
        if (
            self.cfg["walk_enabled"]
            and self.cfg["enabled"]
            and self._schedule_active()
            and not self.walker.busy
            and self.pet.isVisible()
        ):
            self.walker.ambient_walk(self.cfg["walk_crossing_seconds"])
        self._schedule_next_ambient_walk()

    def drink_now(self, mark: bool = True) -> None:
        if not self.pet.isVisible():
            self.pet.show()
        self.pet.play("waving", loops=2)
        self._show_message(pick_message())
        if mark:
            self.reminder.mark_fired()

    def snooze(self) -> None:
        self.reminder.snooze(10)
        self._show_message("Snoozed for 10 minutes. Daisy will remind you!")

    def set_interval(self, minutes: int) -> None:
        self.reminder.set_interval(minutes)
        self.cfg["interval_minutes"] = minutes
        config.save(self.cfg)
        self.tray.set_interval(minutes)

    def set_enabled(self, enabled: bool) -> None:
        self.cfg["enabled"] = enabled
        config.save(self.cfg)

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.cfg)
        if dialog.exec() == QDialog.Accepted:
            self.cfg.update(dialog.values())
            config.save(self.cfg)
            self.reminder.set_interval(self.cfg["interval_minutes"])
            self.tray.set_interval(self.cfg["interval_minutes"])
            self.custom_reminders = CustomReminderStore.from_config_list(
                self.cfg["custom_reminders"]
            )
            self._schedule_next_ambient_walk()
            self._apply_schedule_visibility()


def run() -> None:
    qt_app = QApplication([])
    qt_app.setQuitOnLastWindowClosed(False)
    controller = DaisyApplication(qt_app)
    controller.qt_app.exec()
