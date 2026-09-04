import random
from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication, QDialog

from . import activity, config, liveliness, schedule, tabs
from .bubble import SpeechBubble
from .custom_reminders import CustomReminder, CustomReminderStore
from . import lines, mood, ollama
from .pet_window import PetWindow
from .reminder import WaterReminder, pick_message
from .settings_dialog import SettingsDialog
from .sprites import SpriteSheet
from .tray import DaisyTray
from .walker import Walker

SIP_DURATION_MS = 2700


class _OllamaSignals(QObject):
    finished = Signal(str)


class _OllamaWorker(QRunnable):
    def __init__(self, prompt: str, model: str, url: str) -> None:
        super().__init__()
        self.prompt = prompt
        self.model = model
        self.url = url
        self.signals = _OllamaSignals()

    def run(self) -> None:
        result = ollama.generate_line(self.prompt, self.model, self.url)
        if result:
            self.signals.finished.emit(result)


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
        self.mood_state = mood.load()
        self._last_drag_mood_at = 0.0
        self._bubble_generation = 0
        self.custom_reminders = CustomReminderStore.from_config_list(
            self.cfg["custom_reminders"]
        )
        self.walker = Walker(self.pet)
        self.pet.moved.connect(self._on_pet_moved)
        self.pet.clicked.connect(self._show_next_reminder)
        self.bubble.acknowledged.connect(self._on_bubble_acknowledged)
        self.bubble.ignored.connect(self._on_bubble_ignored)
        self.pet.right_clicked.connect(self._open_pet_menu)
        self.pet.double_clicked.connect(self._vanish_now)
        self.tray = DaisyTray(
            self.sprites.frames("idle")[0],
            drink_now=self.drink_now,
            snooze=self.snooze,
            snooze_custom=self.snooze_custom,
            set_interval=self.set_interval,
            set_enabled=self.set_enabled,
            quit_app=self.qt_app.quit,
            open_settings=self.open_settings,
            interval=self.reminder.interval_minutes,
            enabled=self.cfg["enabled"],
        )
        self._refresh_tray_custom_reminders()
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
        self.activity_watcher = activity.ActivityWatcher()
        self.latest_activity_snapshot = None
        self.activity_timer = QTimer()
        self.activity_timer.setInterval(20_000)
        self.activity_timer.timeout.connect(self._poll_activity)
        self.activity_timer.start()
        self.tab_watcher = tabs.TabWatcher(
            idle_minutes=self.cfg["tab_idle_minutes"],
            min_open=self.cfg["tab_min_open"],
        )
        self.tab_timer = QTimer()
        self.tab_timer.setInterval(60_000)
        self.tab_timer.timeout.connect(self._poll_tabs)
        self.tab_timer.start()
        self._liveliness_rng = random.Random()
        self._liveliness_last_name = None
        self._last_liveliness_chatter_at = None
        self.liveliness_timer = QTimer()
        self.liveliness_timer.setSingleShot(True)
        self.liveliness_timer.timeout.connect(self._on_liveliness_timer)
        self._schedule_next_liveliness()

    def _save_position(self, position) -> None:
        self.cfg["pos"] = [position.x(), position.y()]
        config.save(self.cfg)

    def _on_pet_moved(self, position) -> None:
        self._save_position(position)
        now = datetime.now().timestamp()
        if self.cfg["mood_enabled"] and now - self._last_drag_mood_at >= 3:
            self._last_drag_mood_at = now
            self._play_mood(mood.decide(self._signals(just_dragged=True)))

    def _show_message(self, text: str, actionable: bool = False) -> None:
        self._bubble_generation += 1
        self.bubble.show_message(
            text,
            self.pet.geometry(),
            self.cfg["bubble_seconds"],
            actionable=actionable,
        )

    def _signals(self, **flags: bool) -> mood.MoodSignals:
        minutes_since_ack = None
        if self.mood_state.last_ack_iso:
            try:
                minutes_since_ack = (
                    datetime.now() - datetime.fromisoformat(
                        self.mood_state.last_ack_iso
                    )
                ).total_seconds() / 60
            except ValueError:
                minutes_since_ack = None
        first = self.mood_state.mark_seen(datetime.now().date())
        mood.save(self.mood_state)
        return mood.MoodSignals(
            hour=datetime.now().hour,
            minutes_since_ack=minutes_since_ack,
            snooze_streak=self.mood_state.snooze_streak,
            ignored_streak=self.mood_state.ignored_streak,
            first_appearance_today=first,
            **flags,
        )

    def _play_mood(self, decision: mood.MoodDecision) -> None:
        preferred, fallback = mood.POSE_FOR_MOOD[decision.mood]
        state = preferred if self.sprites.has_custom_state(preferred) else fallback
        self.pet.play(state, loops=1, then="idle")

    def _show_reminder_line(self, line: str, tone: str, actionable: bool = True) -> None:
        self._show_message(line, actionable=actionable)
        if not self.cfg["ollama_enabled"]:
            return
        generation = self._bubble_generation
        worker = _OllamaWorker(
            ollama.build_prompt(tone, 0),
            self.cfg["ollama_model"],
            self.cfg["ollama_url"],
        )
        worker.signals.finished.connect(
            lambda result, token=generation: self._replace_ollama_line(result, token)
        )
        QThreadPool.globalInstance().start(worker)

    def _replace_ollama_line(self, text: str, generation: int) -> None:
        if generation == self._bubble_generation and self.bubble.isVisible():
            self.bubble.set_message_text(text)

    def _open_pet_menu(self) -> None:
        self.tray.menu.popup(QCursor.pos())

    def _show_next_reminder(self) -> None:
        if not self.cfg["enabled"]:
            self._show_message(
                "Reminders are paused — wake me from the tray menu."
            )
            return
        minutes = max(0, round(self.reminder.seconds_remaining / 60))
        if self.cfg["mood_enabled"]:
            decision = mood.decide(self._signals())
            self._show_message(
                f"Next sip in ~{minutes} min — {lines.pick_line(decision.tone)}"
            )
        else:
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

    def _poll_activity(self) -> None:
        if (
            not self.cfg["activity_enabled"]
            or not self.cfg["enabled"]
            or not self._schedule_active()
            or self.walker.busy
        ):
            return
        snapshot = activity.probe()
        if snapshot is None:
            return
        self.latest_activity_snapshot = snapshot
        observation = self.activity_watcher.observe(snapshot)
        if observation is None or self.bubble.isVisible():
            return
        if self.cfg["mood_enabled"]:
            self._play_mood(
                mood.MoodDecision(
                    activity.MOOD_FOR_KIND[observation.kind],
                    observation.tone,
                    observation.kind,
                )
            )
        self._show_message(observation.text)

    def _poll_tabs(self) -> None:
        if (
            not self.cfg["tab_hints_enabled"]
            or not self.cfg["enabled"]
            or not self._schedule_active()
            or self.walker.busy
            or self.bubble.isVisible()
        ):
            return
        snapshot = tabs.probe_tabs()
        if snapshot is None:
            return
        observation = self.tab_watcher.observe(snapshot)
        if observation is None or self.bubble.isVisible():
            return
        if self.cfg["mood_enabled"]:
            self._play_mood(
                mood.MoodDecision(
                    activity.MOOD_FOR_KIND[observation.kind],
                    observation.tone,
                    observation.kind,
                )
            )
        self._show_message(observation.text)

    def _schedule_next_liveliness(self) -> None:
        delay = liveliness.next_delay_seconds(
            self._liveliness_rng,
            self.cfg["liveliness_min_seconds"],
            self.cfg["liveliness_max_seconds"],
        )
        self.liveliness_timer.start(delay * 1000)

    def _on_liveliness_timer(self) -> None:
        try:
            if (
                self.cfg["liveliness_enabled"]
                and self.cfg["enabled"]
                and self._schedule_active()
                and not self.walker.busy
                and self.pet.isVisible()
                and not self.bubble.isVisible()
            ):
                snapshot = self.latest_activity_snapshot
                if snapshot is None or (
                    snapshot.idle_seconds < 15 * 60
                    and not any(
                        hint in snapshot.window.title.lower()
                        for hint in activity.MEETING_HINTS
                    )
                ):
                    behaviour = liveliness.pick(
                        datetime.now().hour,
                        self._liveliness_rng,
                        self._liveliness_last_name,
                    )
                    self._liveliness_last_name = behaviour.name
                    state = (
                        behaviour.preferred
                        if self.sprites.has_custom_state(behaviour.preferred)
                        else behaviour.fallback
                    )
                    self.pet.play(state, loops=behaviour.loops, then="idle")
                    now = datetime.now()
                    if (
                        behaviour.chatter
                        and self._liveliness_rng.randrange(6) == 0
                        and (
                            self._last_liveliness_chatter_at is None
                            or now - self._last_liveliness_chatter_at
                            >= timedelta(minutes=20)
                        )
                    ):
                        self._last_liveliness_chatter_at = now
                        self._show_message(lines.idle_chatter(self._liveliness_rng))
        finally:
            self._schedule_next_liveliness()

    def _start_reminder_walk(
        self,
        message: str,
        act_it_out,
        actionable: bool = False,
        tone: str | None = None,
    ) -> None:
        """Shared walk-in/pause/walk-out cinematic for any reminder kind.

        `act_it_out` plays whatever pose fits (drinking, waving, ...) and
        marks the specific reminder as fired; the message bubble and the
        walk choreography around it are the same either way.
        """
        crossing = self.cfg["walk_crossing_seconds"]
        fraction = self.cfg["walk_drink_fraction"]

        def at_point() -> None:
            act_it_out()
            if tone is None:
                self._show_message(message, actionable=actionable)
            else:
                self._show_reminder_line(message, tone, actionable)
            QTimer.singleShot(
                max(1, self.cfg["bubble_seconds"]) * 1000, self._finish_reminder_walk
            )

        self.walker.reminder_walk_in(crossing, fraction, at_point)

    def _finish_reminder_walk(self) -> None:
        if not self.pet.isVisible():
            return  # already dismissed (e.g. double-click vanish) — nothing to finish
        self.walker.reminder_walk_out(self.cfg["walk_crossing_seconds"], self.pet.hide)

    def _start_water_reminder_walk(self) -> None:
        decision = (
            mood.decide(self._signals())
            if self.cfg["mood_enabled"]
            else None
        )

        def act_it_out() -> None:
            self.pet.start_sip(SIP_DURATION_MS)
            self.reminder.mark_fired()
            if decision is not None:
                QTimer.singleShot(
                    SIP_DURATION_MS,
                    lambda: self._play_mood(decision)
                    if self.pet.isVisible()
                    else None,
                )

        if decision is None:
            line = f"💧 {pick_message()}"
        else:
            line = lines.pick_line(decision.tone)
        self._start_reminder_walk(
            line,
            act_it_out,
            actionable=self.cfg["mood_enabled"],
            tone=decision.tone if decision is not None else None,
        )

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
        if self.cfg["mood_enabled"]:
            decision = mood.decide(self._signals())
            self._play_mood(decision)
            self._show_reminder_line(lines.pick_line(decision.tone), decision.tone)
        else:
            self.pet.play("waving", loops=2)
            self._show_message(pick_message())
        if mark:
            self.reminder.mark_fired()

    def snooze(self) -> None:
        self.reminder.snooze(10)
        if self.cfg["mood_enabled"]:
            self.mood_state.record_snooze()
            mood.save(self.mood_state)
            decision = mood.decide(
                self._signals(just_snoozed=True)
            )
            self._play_mood(decision)
            self._show_message(lines.pick_line(decision.tone))
        else:
            self._show_message("Snoozed for 10 minutes. Daisy will remind you!")

    def _on_bubble_acknowledged(self) -> None:
        if not self.cfg["mood_enabled"]:
            return
        now = datetime.now()
        self.mood_state.record_ack(now)
        mood.save(self.mood_state)
        self._play_mood(mood.decide(self._signals(just_acknowledged=True)))
        self._show_message(lines.ack_line())

    def _on_bubble_ignored(self) -> None:
        if not self.cfg["mood_enabled"]:
            return
        self.mood_state.record_ignored()
        mood.save(self.mood_state)

    def snooze_custom(self, reminder_id: str) -> None:
        item = self.custom_reminders.find(reminder_id)
        if item is None:
            return
        item.snooze()
        self._show_message(f'Snoozed "{item.text}" for {item.snooze_minutes} min.')

    def _refresh_tray_custom_reminders(self) -> None:
        items = [
            (item.reminder_id, item.summary())
            for item in self.custom_reminders.items
            if item.enabled
        ]
        self.tray.set_custom_reminders(items)

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
            self._apply_settings(dialog.values())

    def _apply_settings(self, values: dict) -> None:
        old_scale = self.cfg["scale"]
        self.cfg.update(values)
        if self.cfg["scale"] != old_scale:
            self.pet.rescale(self.cfg["scale"])
            self.pet.move(self.pet.clamp_position(self.pet.pos()))
        config.save(self.cfg)
        self.reminder.set_interval(self.cfg["interval_minutes"])
        self.tray.set_interval(self.cfg["interval_minutes"])
        self.custom_reminders = CustomReminderStore.from_config_list(
            self.cfg["custom_reminders"]
        )
        self.tab_watcher = tabs.TabWatcher(
            idle_minutes=self.cfg["tab_idle_minutes"],
            min_open=self.cfg["tab_min_open"],
        )
        self._refresh_tray_custom_reminders()
        self._schedule_next_ambient_walk()
        self._schedule_next_liveliness()
        self._apply_schedule_visibility()


def run() -> None:
    qt_app = QApplication([])
    qt_app.setQuitOnLastWindowClosed(False)
    controller = DaisyApplication(qt_app)
    controller.qt_app.exec()
