from collections.abc import Callable

from PySide6.QtGui import QActionGroup, QCursor, QIcon, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon


class DaisyTray:
    def __init__(
        self,
        idle_frame: QPixmap,
        *,
        drink_now: Callable[[], None],
        snooze: Callable[[], None],
        snooze_custom: Callable[[str], None],
        set_interval: Callable[[int], None],
        set_enabled: Callable[[bool], None],
        quit_app: Callable[[], None],
        open_settings: Callable[[], None],
        interval: int,
        enabled: bool,
    ) -> None:
        self.icon = QSystemTrayIcon(QIcon(idle_frame))
        menu = QMenu()
        self.menu = menu
        self.icon.setContextMenu(menu)
        self.icon.activated.connect(self._on_activated)
        drink = menu.addAction("Drink now")
        drink.triggered.connect(lambda: drink_now())
        snooze_action = menu.addAction("Snooze 10 minutes")
        snooze_action.triggered.connect(lambda: snooze())
        self._snooze_custom_callback = snooze_custom
        self.snooze_custom_menu = menu.addMenu("Snooze a reminder")
        self.custom_snooze_actions: dict[str, object] = {}
        self.set_custom_reminders([])
        interval_menu = menu.addMenu("Interval")
        self.interval_actions = {}
        interval_group = QActionGroup(interval_menu)
        interval_group.setExclusive(True)
        for minutes in (15, 30, 45, 60):
            action = interval_menu.addAction(f"{minutes} minutes")
            action.setCheckable(True)
            interval_group.addAction(action)
            action.triggered.connect(
                lambda checked, value=minutes: set_interval(value)
            )
            self.interval_actions[minutes] = action
        if interval in self.interval_actions:
            self.interval_actions[interval].setChecked(True)
        enabled_action = menu.addAction("Reminders enabled")
        enabled_action.setCheckable(True)
        enabled_action.setChecked(enabled)
        enabled_action.toggled.connect(set_enabled)
        menu.addSeparator()
        settings_action = menu.addAction("Daisy Settings...")
        settings_action.triggered.connect(lambda: open_settings())
        menu.addSeparator()
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(quit_app)
        self.enabled_action = enabled_action

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.menu.popup(QCursor.pos())

    def set_custom_reminders(self, items: list[tuple[str, str]]) -> None:
        """Rebuild the "Snooze a reminder" submenu. `items` is a list of
        (reminder_id, label) pairs for the currently enabled custom reminders.
        """
        self.snooze_custom_menu.clear()
        self.custom_snooze_actions = {}
        if not items:
            placeholder = self.snooze_custom_menu.addAction("(none yet)")
            placeholder.setEnabled(False)
            return
        for reminder_id, label in items:
            action = self.snooze_custom_menu.addAction(label)
            action.triggered.connect(
                lambda checked, rid=reminder_id: self._snooze_custom_callback(rid)
            )
            self.custom_snooze_actions[reminder_id] = action

    def set_interval(self, minutes: int) -> None:
        if minutes in self.interval_actions:
            self.interval_actions[minutes].setChecked(True)

    def set_enabled(self, enabled: bool) -> None:
        self.enabled_action.setChecked(enabled)

    def show(self) -> None:
        self.icon.show()
