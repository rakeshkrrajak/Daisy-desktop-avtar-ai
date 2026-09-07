from datetime import date, datetime, timedelta
import random
from types import SimpleNamespace

from PySide6.QtCore import QPoint, QRect, QSize

from daisy_pet.activity import ActivitySnapshot, Observation, WindowInfo
from daisy_pet.app import DaisyApplication, SIP_DURATION_MS
from daisy_pet.config import DEFAULTS
from daisy_pet.liveliness import Behaviour
from daisy_pet.memory import DaySummary, Note
from daisy_pet.mood import MoodDecision
from daisy_pet.tabs import TabInfo, TabSnapshot


def test_water_walk_plays_mood_after_sip(monkeypatch, qapp):
    events = []
    callbacks = []
    decision = MoodDecision("happy", "cheerful", "test")
    app = DaisyApplication.__new__(DaisyApplication)
    app.cfg = {
        "mood_enabled": True,
        "bubble_seconds": 12,
        "reminder_wait_seconds": 120,
        "walk_crossing_seconds": 8,
        "walk_drink_fraction": 0.4,
    }
    app._tab_review_prompt = False
    app.tab_review = SimpleNamespace(active=False)
    app.pet = SimpleNamespace(
        isVisible=lambda: True,
        start_sip=lambda duration: events.append(("sip", duration)),
    )
    app.reminder = SimpleNamespace(mark_fired=lambda: events.append("fired"))
    app.walker = SimpleNamespace(
        reminder_walk_in=lambda crossing, fraction, callback: callback()
    )
    app._signals = lambda: None
    app._show_reminder_choice = lambda line, tone: events.append(
        ("choice", line, tone)
    )
    app._play_mood = lambda value: events.append(("mood", value.mood))
    monkeypatch.setattr(
        "daisy_pet.app.mood.decide", lambda signals: decision
    )
    monkeypatch.setattr(
        "daisy_pet.app.lines.pick_line", lambda tone: "Drink up!"
    )
    monkeypatch.setattr(
        "daisy_pet.app.QTimer.singleShot",
        lambda delay, callback: callbacks.append((delay, callback)),
    )

    app._start_water_reminder_walk()

    assert events[0:2] == [("sip", SIP_DURATION_MS), "fired"]
    assert not any(event[0] == "mood" for event in events if isinstance(event, tuple))
    assert callbacks and callbacks[0][0] == SIP_DURATION_MS
    callbacks[0][1]()
    assert ("mood", "happy") in events


def test_activity_message_abandons_pending_reminder_choice(monkeypatch):
    events = []
    app = DaisyApplication.__new__(DaisyApplication)
    app.cfg = {
        "activity_enabled": True,
        "enabled": True,
        "schedule_enabled": False,
        "mood_enabled": True,
        "bubble_seconds": 12,
    }
    app.walker = SimpleNamespace(busy=False)
    app._schedule_active = lambda: True
    app._reminder_choice_active = True
    app._bubble_generation = 0
    app.memory = None
    app.mood_state = SimpleNamespace(
        record_ignored=lambda: events.append("ignored")
    )
    app._finish_reminder_walk = lambda: events.append("finish")
    app.bubble = SimpleNamespace(
        isVisible=lambda: False,
        show_message=lambda *args, **kwargs: events.append("message"),
    )
    app.pet = SimpleNamespace(
        geometry=lambda: QRect(10, 20, 50, 60),
        isVisible=lambda: True,
    )
    app.activity_watcher = SimpleNamespace(
        observe=lambda snapshot: Observation("sitting", "Stretch?", "gentle")
    )
    monkeypatch.setattr(
        "daisy_pet.app.activity.probe",
        lambda: ActivitySnapshot(
            WindowInfo("Editor", "code.exe"), 0, 0, datetime.now()
        ),
    )
    monkeypatch.setattr("daisy_pet.app.mood.save", lambda state: None)
    app._play_mood = lambda decision: None

    app._poll_activity()

    assert app._reminder_choice_active is False
    assert events == ["ignored", "finish", "message"]


def test_tickled_plays_mood_and_shows_line(monkeypatch):
    events = []
    app = DaisyApplication.__new__(DaisyApplication)
    app.cfg = {"mood_enabled": True}
    app.pet = SimpleNamespace(is_walking=False)
    app._reminder_choice_active = False
    app._tab_review_prompt = False
    app.tab_review = SimpleNamespace(active=False)
    app._last_tickle_at = 0.0
    app._signals = lambda **flags: events.append(("signals", flags))
    app._play_mood = lambda decision: events.append(("mood", decision.mood))
    app._show_message = lambda text: events.append(("line", text))
    monkeypatch.setattr(
        "daisy_pet.app.mood.decide",
        lambda signals: MoodDecision("happy", "cheerful", "just_tickled"),
    )
    monkeypatch.setattr(
        "daisy_pet.app.lines.tickle_line", lambda: "Hehe — that tickles!"
    )

    app._on_tickled()
    app._on_tickled()

    assert events[0] == ("signals", {"just_tickled": True})
    assert ("mood", "happy") in events
    assert ("line", "Hehe — that tickles!") in events
    assert events.count(("line", "Hehe — that tickles!")) == 1


def test_tickled_is_ignored_during_reminder_or_walk(monkeypatch):
    shown = []
    app = DaisyApplication.__new__(DaisyApplication)
    app.cfg = {"mood_enabled": False}
    app.pet = SimpleNamespace(is_walking=False, play=lambda *args, **kwargs: None)
    app._reminder_choice_active = True
    app._tab_review_prompt = False
    app.tab_review = SimpleNamespace(active=False)
    app._last_tickle_at = 0.0
    app._show_message = lambda text: shown.append(text)

    app._on_tickled()
    app._reminder_choice_active = False
    app.pet.is_walking = True
    app._on_tickled()

    assert shown == []


def test_tab_review_prompt_abandons_pending_reminder_choice(monkeypatch):
    events = []
    app = DaisyApplication.__new__(DaisyApplication)
    app.cfg = {
        "tab_hints_enabled": True,
        "tab_review_enabled": True,
        "enabled": True,
        "schedule_enabled": False,
        "mood_enabled": True,
        "bubble_seconds": 12,
    }
    app.walker = SimpleNamespace(busy=False)
    app._schedule_active = lambda: True
    app._reminder_choice_active = True
    app._bubble_generation = 0
    app.memory = None
    app.mood_state = SimpleNamespace(
        record_ignored=lambda: events.append("ignored")
    )
    app._finish_reminder_walk = lambda: events.append("finish")
    app.bubble = SimpleNamespace(
        isVisible=lambda: False,
        show_choice=lambda *args, **kwargs: events.append("prompt"),
    )
    app.pet = SimpleNamespace(
        geometry=lambda: QRect(10, 20, 50, 60),
        isVisible=lambda: True,
    )
    app.tab_watcher = SimpleNamespace(
        last_stale_tabs=(),
        observe=lambda snapshot: Observation(
            "stale_tabs", "Close these?", "firm"
        ),
    )
    app.tab_review = SimpleNamespace(active=False)
    app._tab_review_prompt = False
    monkeypatch.setattr(
        "daisy_pet.app.tabs.probe_tabs",
        lambda: TabSnapshot((), datetime.now(), "windows"),
    )
    monkeypatch.setattr("daisy_pet.app.mood.save", lambda state: None)
    app._play_mood = lambda decision: None

    app._poll_tabs()

    assert app._reminder_choice_active is False
    assert events == ["ignored", "finish", "prompt"]


def test_tab_review_prompt_brings_daisy_back_before_the_bubble(monkeypatch):
    events = []
    app = DaisyApplication.__new__(DaisyApplication)
    app.cfg = {
        "tab_hints_enabled": True,
        "tab_review_enabled": True,
        "enabled": True,
        "schedule_enabled": False,
        "mood_enabled": False,
        "bubble_seconds": 12,
    }
    app.walker = SimpleNamespace(busy=False)
    app._reminder_choice_active = False
    app._bubble_generation = 0
    app.memory = None
    app.bubble = SimpleNamespace(
        isVisible=lambda: False,
        show_choice=lambda *args, **kwargs: events.append("prompt"),
    )
    app.pet = SimpleNamespace(
        geometry=lambda: QRect(10, 20, 50, 60),
        isVisible=lambda: False,
        show_at_right_corner=lambda: events.append("shown"),
    )
    app.tab_watcher = SimpleNamespace(
        last_stale_tabs=(),
        observe=lambda snapshot: Observation(
            "stale_tabs", "Close these?", "firm"
        ),
    )
    app.tab_review = SimpleNamespace(active=False)
    app._tab_review_prompt = False
    monkeypatch.setattr(
        "daisy_pet.app.tabs.probe_tabs",
        lambda: TabSnapshot((), datetime.now(), "windows"),
    )

    app._poll_tabs()

    assert events == ["shown", "prompt"]


def test_reminder_ack_choice_does_not_record_ignored(monkeypatch):
    events = []
    app = DaisyApplication.__new__(DaisyApplication)
    app.cfg = {"mood_enabled": True}
    app._reminder_choice_active = True
    app.memory = None
    app.mood_state = SimpleNamespace(
        record_ack=lambda now: events.append("ack"),
        record_ignored=lambda: events.append("ignored"),
    )
    app._signals = lambda **flags: None
    app._play_mood = lambda decision: None
    app._show_message = lambda text: events.append("message")
    app._finish_reminder_walk = lambda: events.append("finish")
    monkeypatch.setattr("daisy_pet.app.mood.save", lambda state: None)
    monkeypatch.setattr(
        "daisy_pet.app.mood.decide",
        lambda signals: MoodDecision("happy", "cheerful", "ack"),
    )
    monkeypatch.setattr(
        "daisy_pet.app.QTimer.singleShot",
        lambda delay, callback: events.append(delay),
    )

    app._on_bubble_choice("I drank it")

    assert "ack" in events
    assert "ignored" not in events


def test_water_reminder_waits_for_choice_without_walkout_timer(monkeypatch, qapp):
    callbacks = []
    app = DaisyApplication.__new__(DaisyApplication)
    app.cfg = {
        "mood_enabled": False,
        "ollama_enabled": False,
        "reminder_wait_seconds": 120,
        "walk_crossing_seconds": 8,
        "walk_drink_fraction": 0.4,
    }
    app._tab_review_prompt = False
    app.tab_review = SimpleNamespace(active=False)
    app.pet = SimpleNamespace(
        start_sip=lambda duration: None,
        isVisible=lambda: True,
    )
    app.reminder = SimpleNamespace(mark_fired=lambda: None)
    app.walker = SimpleNamespace(
        reminder_walk_in=lambda crossing, fraction, callback: callback()
    )
    app._show_reminder_choice = lambda line, tone: None
    monkeypatch.setattr(
        "daisy_pet.app.QTimer.singleShot",
        lambda delay, callback: callbacks.append((delay, callback)),
    )

    app._start_water_reminder_walk()

    assert callbacks == []


def test_reminder_choice_acknowledgement_records_and_walks_out(monkeypatch):
    events = []
    app = DaisyApplication.__new__(DaisyApplication)
    app.cfg = {"mood_enabled": False}
    app._reminder_choice_active = True
    app.memory = None
    app.reminder = SimpleNamespace()
    app._show_message = lambda text: events.append(("message", text))
    app._finish_reminder_walk = lambda: events.append("finish")
    monkeypatch.setattr(
        "daisy_pet.app.QTimer.singleShot",
        lambda delay, callback: (events.append(delay), callback()),
    )

    app._on_bubble_choice("I drank it")

    assert events[0][0] == "message"
    assert events[1:] == [1200, "finish"]
    assert app._reminder_choice_active is False


def test_reminder_choice_snoozes_five_minutes_and_walks_out(monkeypatch):
    events = []
    app = DaisyApplication.__new__(DaisyApplication)
    app.cfg = {"mood_enabled": False}
    app._reminder_choice_active = True
    app.memory = None
    app.reminder = SimpleNamespace(
        snooze=lambda minutes: events.append(("snooze", minutes))
    )
    app._show_message = lambda text: events.append(("message", text))
    app._finish_reminder_walk = lambda: events.append("finish")
    monkeypatch.setattr(
        "daisy_pet.app.QTimer.singleShot",
        lambda delay, callback: (events.append(delay), callback()),
    )

    app._on_bubble_choice("Snooze 5 min")

    assert ("snooze", 5) in events
    assert any(event[0] == "message" for event in events if isinstance(event, tuple))
    assert events[-2:] == [1200, "finish"]


def test_reminder_choice_expiry_records_ignore_and_walks_out(monkeypatch):
    events = []
    app = DaisyApplication.__new__(DaisyApplication)
    app.cfg = {"mood_enabled": True}
    app._reminder_choice_active = True
    app.memory = None
    app.mood_state = SimpleNamespace(
        record_ignored=lambda: events.append("ignored")
    )
    app._finish_reminder_walk = lambda: events.append("finish")
    monkeypatch.setattr("daisy_pet.app.mood.save", lambda state: None)

    app._on_bubble_ignored()

    assert events == ["ignored", "finish"]
    assert app._reminder_choice_active is False


def test_activity_poll_is_gated(monkeypatch, qapp):
    snapshot = ActivitySnapshot(
        WindowInfo("Editor", "code.exe"), 0, 0, datetime.now()
    )
    observation = Observation("sitting", "Stretch and sip?", "gentle")
    shown = []
    app = DaisyApplication.__new__(DaisyApplication)
    app.cfg = {
        "activity_enabled": True,
        "enabled": True,
        "schedule_enabled": False,
    }
    app.walker = SimpleNamespace(busy=False)
    app.bubble = SimpleNamespace(isVisible=lambda: False)
    app.activity_watcher = SimpleNamespace(observe=lambda value: observation)
    app._schedule_active = lambda: True
    app._show_message = lambda text: shown.append(text)
    app._play_mood = lambda decision: None
    monkeypatch.setattr("daisy_pet.app.activity.probe", lambda: snapshot)

    app.cfg["enabled"] = False
    app._poll_activity()
    app.cfg["enabled"] = True
    app._schedule_active = lambda: False
    app._poll_activity()
    app._schedule_active = lambda: True
    app.walker.busy = True
    app._poll_activity()
    assert shown == []


def test_tab_poll_is_gated(monkeypatch):
    shown = []
    app = DaisyApplication.__new__(DaisyApplication)
    app.cfg = {
        "tab_hints_enabled": True,
        "tab_review_enabled": True,
        "enabled": True,
        "schedule_enabled": False,
        "mood_enabled": True,
    }
    app.walker = SimpleNamespace(busy=False)
    app.bubble = SimpleNamespace(isVisible=lambda: False)
    app.tab_watcher = SimpleNamespace(observe=lambda value: Observation(
        "stale_tabs", "Close these?", "firm"
    ))
    app.tab_review = SimpleNamespace(active=True)
    app._schedule_active = lambda: True
    app._show_message = lambda text: shown.append(text)
    app._play_mood = lambda decision: None
    monkeypatch.setattr(
        "daisy_pet.app.tabs.probe_tabs",
        lambda: TabSnapshot(
            (TabInfo("1:x", "x", "chrome.exe", False),),
            datetime.now(),
            "windows",
        ),
    )

    app.cfg["enabled"] = False
    app._poll_tabs()
    app.cfg["enabled"] = True
    app._schedule_active = lambda: False
    app._poll_tabs()
    app._schedule_active = lambda: True
    app.walker.busy = True
    app._poll_tabs()
    app.walker.busy = False
    app.bubble = SimpleNamespace(isVisible=lambda: True)
    app._poll_tabs()
    assert shown == []


def test_liveliness_timer_is_gated_by_context(monkeypatch):
    shown = []
    played = []
    app = DaisyApplication.__new__(DaisyApplication)
    app.cfg = {
        "liveliness_enabled": True,
        "enabled": True,
        "schedule_enabled": False,
        "liveliness_min_seconds": 45,
        "liveliness_max_seconds": 150,
    }
    app._tab_review_prompt = False
    app.tab_review = SimpleNamespace(active=False)
    app.walker = SimpleNamespace(busy=False)
    app.pet = SimpleNamespace(
        isVisible=lambda: True,
        play=lambda *args, **kwargs: played.append(args),
    )
    app.bubble = SimpleNamespace(isVisible=lambda: False)
    app.sprites = SimpleNamespace(has_custom_state=lambda state: False)
    app._schedule_active = lambda: True
    app._show_message = lambda text: shown.append(text)
    app._liveliness_rng = random.Random(1)
    app._liveliness_last_name = None
    app._last_liveliness_chatter_at = None
    app.liveliness_timer = SimpleNamespace(start=lambda value: None)
    app.latest_activity_snapshot = ActivitySnapshot(
        WindowInfo("Microsoft Teams meeting", "teams.exe"),
        0,
        0,
        datetime.now(),
    )
    monkeypatch.setattr(
        "daisy_pet.app.liveliness.pick",
        lambda hour, rng, last: Behaviour("test", "happy", "waving", 1, False),
    )
    app._on_liveliness_timer()
    assert played == []
    app.latest_activity_snapshot = ActivitySnapshot(
        WindowInfo("Editor", "code.exe"),
        15 * 60,
        0,
        datetime.now(),
    )
    app._on_liveliness_timer()
    assert played == []

    app.latest_activity_snapshot = None
    app.cfg["enabled"] = False
    app._on_liveliness_timer()
    assert played == []


def test_review_suppresses_tab_poll_and_liveliness(monkeypatch):
    app = DaisyApplication.__new__(DaisyApplication)
    app.cfg = {
        "tab_hints_enabled": True,
        "enabled": True,
        "schedule_enabled": False,
        "liveliness_enabled": True,
        "liveliness_min_seconds": 45,
        "liveliness_max_seconds": 150,
    }
    app.walker = SimpleNamespace(busy=False)
    app.tab_review = SimpleNamespace(active=True)
    app._tab_review_prompt = False
    app.bubble = SimpleNamespace(isVisible=lambda: False)
    app.tab_watcher = SimpleNamespace(
        observe=lambda value: (_ for _ in ()).throw(AssertionError("polled"))
    )
    app._schedule_active = lambda: True
    app._liveliness_rng = random.Random(1)
    app._liveliness_last_name = None
    app._last_liveliness_chatter_at = None
    app.latest_activity_snapshot = None
    app.pet = SimpleNamespace(isVisible=lambda: True, play=lambda *a, **k: None)
    app.sprites = SimpleNamespace(has_custom_state=lambda state: False)
    app.liveliness_timer = SimpleNamespace(start=lambda value: None)
    app._poll_tabs()
    app._on_liveliness_timer()


def test_due_reminder_cancels_review_and_restores_position():
    app = DaisyApplication.__new__(DaisyApplication)
    app.cfg = {
        "enabled": True,
        "schedule_enabled": False,
        "walk_enabled": False,
    }
    app.walker = SimpleNamespace(busy=False)
    app.reminder = SimpleNamespace(due=lambda: True)
    app.custom_reminders = SimpleNamespace(due_items=lambda: [])
    app.tab_review = SimpleNamespace(
        active=True,
        cancel=lambda: setattr(app.tab_review, "active", False),
    )
    app._tab_review_prompt = False
    app._pending_review_tabs = ()
    app._tab_review_position = QPoint(10, 20)
    app._tab_review_started_at = datetime.now()
    app.tab_review_timer = SimpleNamespace(stop=lambda: None)
    positions = []
    app.pet = SimpleNamespace(
        move=lambda position: positions.append(position),
        isVisible=lambda: True,
        play=lambda *a, **k: None,
    )
    app.bubble = SimpleNamespace(hide=lambda: None)
    app._schedule_active = lambda: True
    app._apply_schedule_visibility = lambda: None
    fired = []
    app.drink_now = lambda mark=True: fired.append(mark)

    app._poll_reminder()

    assert positions == [QPoint(10, 20)]
    assert fired == [True]
    assert not app.tab_review.active


def test_review_timeout_resets_after_closed_step(monkeypatch):
    app = DaisyApplication.__new__(DaisyApplication)
    app.cfg = {"mood_enabled": False}
    app.tab_review = SimpleNamespace(
        active=True,
        current=lambda: None,
        sync=lambda snapshot: "closed",
    )
    app.memory = None
    app.tab_review_timer = SimpleNamespace(stop=lambda: None)
    app._tab_review_started_at = datetime.now() - timedelta(seconds=59)
    app._present_tab_review = lambda: None
    monkeypatch.setattr(
        "daisy_pet.app.tabs.probe_tabs",
        lambda: TabSnapshot((), datetime.now(), "windows"),
    )

    before = app._tab_review_started_at
    app._poll_tab_review()

    assert app._tab_review_started_at > before


def _scale_test_app(busy, monkeypatch):
    events = []
    app = DaisyApplication.__new__(DaisyApplication)
    app.cfg = {**DEFAULTS, "scale": 1.0}
    app.pet = SimpleNamespace(
        rescale=lambda scale: events.append(("rescale", scale)),
        pos=lambda: QPoint(10, 20),
        clamp_position=lambda position: events.append(("clamp", position))
        or QPoint(10, 20),
        move=lambda position: events.append(("move", position)),
        place_right_corner=lambda: events.append("corner"),
    )
    app.walker = SimpleNamespace(busy=busy)
    app.memory = None
    app._flush_usage = lambda: None
    app._prune_memory = lambda: None
    app.reminder = SimpleNamespace(set_interval=lambda value: None)
    app.tray = SimpleNamespace(set_interval=lambda value: None)
    app._refresh_tray_custom_reminders = lambda: None
    app._schedule_next_ambient_walk = lambda: None
    app._schedule_next_liveliness = lambda: None
    app._apply_schedule_visibility = lambda: None
    monkeypatch.setattr("daisy_pet.app.config.save", lambda cfg: None)
    return app, events


def test_scale_change_replaces_idle_daisy_at_right_corner(monkeypatch):
    app, events = _scale_test_app(False, monkeypatch)

    app._apply_settings({"scale": 1.5})

    assert events[:2] == [("rescale", 1.5), "corner"]


def test_scale_change_clamps_daisy_during_walk(monkeypatch):
    app, events = _scale_test_app(True, monkeypatch)

    app._apply_settings({"scale": 1.5})

    assert events[0] == ("rescale", 1.5)
    assert events[1][0] == "clamp"
    assert "corner" not in events


def test_review_bubble_uses_moved_to_anchor(monkeypatch):
    app = DaisyApplication.__new__(DaisyApplication)
    app.cfg = {"bubble_seconds": 12, "schedule_enabled": False}
    app.tab_review = SimpleNamespace(
        current=lambda: TabInfo(
            "key", "Jenkins", "chrome.exe", False, rect=(100, 200, 300, 240)
        )
    )
    app._tab_review_started_at = None
    app.pet = SimpleNamespace(
        width=lambda: 50,
        size=lambda: QSize(50, 60),
        clamp_position=lambda position: QPoint(30, 40),
        move=lambda position: None,
        play=lambda *args, **kwargs: None,
        geometry=lambda: QRect(900, 900, 50, 60),
        isVisible=lambda: True,
    )
    anchors = []
    app.bubble = SimpleNamespace(
        show_choice=lambda text, near, seconds, choices: anchors.append(near)
    )
    monkeypatch.setattr("daisy_pet.app.tabs.focus_tab", lambda key: True)

    app._present_tab_review()

    assert anchors[0].topLeft() == QPoint(30, 40)


def test_review_bubble_expiry_cancels_and_restores_position():
    app = DaisyApplication.__new__(DaisyApplication)
    app.cfg = {}
    app._reminder_choice_active = False
    app.tab_review = SimpleNamespace(
        active=True,
        cancel=lambda: setattr(app.tab_review, "active", False),
    )
    app._tab_review_prompt = False
    app._pending_review_tabs = ()
    app._tab_review_position = QPoint(10, 20)
    app._tab_review_started_at = datetime.now()
    app.tab_review_timer = SimpleNamespace(stop=lambda: None)
    positions = []
    app.pet = SimpleNamespace(
        move=lambda position: positions.append(position),
        isVisible=lambda: True,
        play=lambda *a, **k: None,
    )
    app.bubble = SimpleNamespace(hide=lambda: None)

    app._on_bubble_ignored()

    assert positions == [QPoint(10, 20)]
    assert not app.tab_review.active
    assert app._tab_review_started_at is None


def test_bubble_expiry_outside_review_records_ignored(monkeypatch):
    app = DaisyApplication.__new__(DaisyApplication)
    app.cfg = {"mood_enabled": True}
    app.memory = None
    app._reminder_choice_active = False
    app.tab_review = SimpleNamespace(active=False)
    app._tab_review_prompt = False
    app.mood_state = SimpleNamespace(record_ignored=lambda: setattr(
        app.mood_state, "ignored", True
    ))
    monkeypatch.setattr("daisy_pet.app.mood.save", lambda state: None)

    app._on_bubble_ignored()

    assert app.mood_state.ignored is True


def _frozen_datetime(moment):
    return type(
        "_FrozenDatetime",
        (datetime,),
        {"now": classmethod(lambda cls: moment)},
    )


class _FakeMemory:
    def __init__(self, summary=None):
        self.usage = []
        self.hydration = []
        self.tabs = []
        self.notes = []
        self.pruned = []
        self.closed = False
        self._summary = summary or DaySummary(day="2026-03-04")

    def record_app_usage(self, day, process, seconds):
        self.usage.append((day, process, seconds))

    def record_hydration(self, kind):
        self.hydration.append(kind)

    def record_tab_decision(self, kind, title):
        self.tabs.append((kind, title))

    def add_note(self, text, due_date=None):
        self.notes.append((text, due_date))
        return len(text) <= 200

    def summary(self, day):
        return self._summary

    def prune(self, cutoff):
        self.pruned.append(cutoff)

    def close(self):
        self.closed = True


def _summary_app(store, **cfg):
    app = DaisyApplication.__new__(DaisyApplication)
    app.cfg = {
        **DEFAULTS,
        "summary_enabled": True,
        "memory_enabled": True,
        "enabled": True,
        "walk_enabled": False,
        **cfg,
    }
    app.memory = store
    app.usage = SimpleNamespace(flush=lambda: None, observe=lambda *args: None)
    app._summary_shown_on = None
    app._reminder_choice_active = False
    app._tab_review_prompt = False
    app.tab_review = SimpleNamespace(active=False)
    app.walker = SimpleNamespace(busy=False)
    app.bubble = SimpleNamespace(isVisible=lambda: False)
    return app


def test_records_app_usage_from_activity_polls(monkeypatch):
    store = _FakeMemory()
    app = DaisyApplication.__new__(DaisyApplication)
    app.memory = store
    observed = []

    def observe(process, at, idle_seconds):
        observed.append((process, idle_seconds))
        return ("2026-03-04", process, 60)

    app.usage = SimpleNamespace(observe=observe)
    snapshot = ActivitySnapshot(
        WindowInfo("Secret document", "code.exe"), 5, 2, datetime.now()
    )

    app._record_usage(snapshot)

    assert observed == [("code.exe", 5)]
    assert store.usage == [("2026-03-04", "code.exe", 60)]


def test_usage_recording_is_skipped_when_memory_is_off():
    app = DaisyApplication.__new__(DaisyApplication)
    app.memory = None
    app.usage = SimpleNamespace(
        observe=lambda *args: (_ for _ in ()).throw(AssertionError("observed"))
    )
    app._record_usage(
        ActivitySnapshot(WindowInfo("t", "code.exe"), 0, 0, datetime.now())
    )


def test_hydration_outcomes_are_recorded(monkeypatch):
    store = _FakeMemory()
    app = DaisyApplication.__new__(DaisyApplication)
    app.cfg = {**DEFAULTS, "mood_enabled": False}
    app.memory = store
    app._reminder_choice_active = True
    app._show_message = lambda text: None
    app.reminder = SimpleNamespace(snooze=lambda minutes: None)
    app._finish_reminder_walk = lambda: None
    monkeypatch.setattr(
        "daisy_pet.app.QTimer.singleShot", lambda delay, callback: None
    )

    app._on_bubble_choice("I drank it")
    app._reminder_choice_active = True
    app._on_bubble_choice("Snooze 5 min")
    app._reminder_choice_active = True
    app.mood_state = SimpleNamespace(record_ignored=lambda: None)
    app._abandon_reminder_choice()

    assert store.hydration == [
        "hydration_ack",
        "hydration_snooze",
        "hydration_ignored",
    ]


def test_hydration_is_recorded_when_the_bubble_itself_is_clicked():
    store = _FakeMemory()
    app = DaisyApplication.__new__(DaisyApplication)
    app.cfg = {**DEFAULTS, "mood_enabled": False}
    app.memory = store

    app._on_bubble_acknowledged()

    assert store.hydration == ["hydration_ack"]


def test_hydration_is_recorded_when_an_actionable_bubble_expires():
    store = _FakeMemory()
    app = DaisyApplication.__new__(DaisyApplication)
    app.cfg = {**DEFAULTS, "mood_enabled": False}
    app.memory = store
    app._reminder_choice_active = False
    app._tab_review_prompt = False
    app.tab_review = SimpleNamespace(active=False)

    app._on_bubble_ignored()

    assert store.hydration == ["hydration_ignored"]


def test_hydration_is_recorded_when_snoozed_from_the_tray():
    store = _FakeMemory()
    app = DaisyApplication.__new__(DaisyApplication)
    app.cfg = {**DEFAULTS, "mood_enabled": False}
    app.memory = store
    app.reminder = SimpleNamespace(snooze=lambda minutes: None)
    app._show_message = lambda text: None

    app.snooze()

    assert store.hydration == ["hydration_snooze"]


def test_tab_decisions_are_recorded_by_title_for_hashing(monkeypatch):
    store = _FakeMemory()
    app = DaisyApplication.__new__(DaisyApplication)
    app.cfg = {**DEFAULTS}
    app.memory = store
    app._reminder_choice_active = False
    app._tab_review_prompt = False
    kept = TabInfo("k1", "Kept article", None, None)
    app.tab_review = SimpleNamespace(
        active=True,
        current=lambda: kept,
        keep_current=lambda today: None,
    )
    app._present_tab_review = lambda: None

    app._on_bubble_choice("Keep it")

    assert store.tabs == [("tab_kept", "Kept article")]


def test_summary_is_shown_on_demand(monkeypatch):
    store = _FakeMemory(
        DaySummary(day="2026-03-04", notes=(Note(text="call Manisha"),))
    )
    app = _summary_app(store)
    shown = []
    app._show_message = lambda text: shown.append(text)
    app.pet = SimpleNamespace(
        isVisible=lambda: True, play=lambda *args, **kwargs: None
    )

    app.show_day_summary()

    assert shown and "1 note" in shown[0]


def test_on_demand_summary_never_interrupts_a_pending_choice_or_review():
    store = _FakeMemory()
    app = _summary_app(store)
    app._show_message = lambda text: (_ for _ in ()).throw(
        AssertionError("interrupted")
    )
    app.pet = SimpleNamespace(isVisible=lambda: True, play=lambda *a, **k: None)

    app._reminder_choice_active = True
    app.show_day_summary()
    app._reminder_choice_active = False
    app._tab_review_prompt = True
    app.show_day_summary()


def test_summary_says_so_when_memory_is_off():
    app = _summary_app(None)
    assert "memory is switched off" in app._day_summary_text()


def test_automatic_summary_respects_gates_and_fires_once(monkeypatch):
    store = _FakeMemory(DaySummary(day="2026-03-04", tabs_kept=2))
    app = _summary_app(store, summary_time="18:00")
    shown = []
    app._show_message = lambda text: shown.append(text)
    app.pet = SimpleNamespace(
        isVisible=lambda: True, play=lambda *args, **kwargs: None
    )
    app._schedule_active = lambda: True
    monkeypatch.setattr(
        "daisy_pet.app.datetime",
        _frozen_datetime(datetime(2026, 3, 4, 17, 59)),
    )
    app._poll_summary()
    assert shown == []

    monkeypatch.setattr(
        "daisy_pet.app.datetime",
        _frozen_datetime(datetime(2026, 3, 4, 18, 1)),
    )
    app._poll_summary()
    app._poll_summary()
    assert len(shown) == 1


def test_automatic_summary_is_blocked_by_water_choice_and_tab_review(monkeypatch):
    store = _FakeMemory(DaySummary(day="2026-03-04", tabs_kept=2))
    app = _summary_app(store)
    app._show_message = lambda text: (_ for _ in ()).throw(
        AssertionError("interrupted")
    )
    app.pet = SimpleNamespace(isVisible=lambda: True, play=lambda *a, **k: None)
    app._schedule_active = lambda: True
    monkeypatch.setattr(
        "daisy_pet.app.datetime",
        _frozen_datetime(datetime(2026, 3, 4, 18, 1)),
    )

    app._reminder_choice_active = True
    app._poll_summary()
    app._reminder_choice_active = False
    app.tab_review = SimpleNamespace(active=True)
    app._poll_summary()
    app.tab_review = SimpleNamespace(active=False)
    app.bubble = SimpleNamespace(isVisible=lambda: True)
    app._poll_summary()
    app.bubble = SimpleNamespace(isVisible=lambda: False)
    app.cfg["summary_enabled"] = False
    app._poll_summary()
    assert app._summary_shown_on is None


def test_memory_is_pruned_with_the_configured_retention(monkeypatch):
    store = _FakeMemory()
    app = DaisyApplication.__new__(DaisyApplication)
    app.cfg = {**DEFAULTS, "memory_retention_days": 7}
    app.memory = store

    app._prune_memory()

    assert store.pruned == [date.today() - timedelta(days=7)]


def test_disabling_memory_in_settings_flushes_and_closes_it(monkeypatch):
    store = _FakeMemory()
    app = DaisyApplication.__new__(DaisyApplication)
    app.cfg = {**DEFAULTS, "memory_enabled": True}
    app.memory = store
    app.usage = SimpleNamespace(flush=lambda: ("2026-03-04", "code.exe", 60))
    app._cancel_tab_review = lambda: None
    app.pet = SimpleNamespace()
    app.reminder = SimpleNamespace(set_interval=lambda minutes: None)
    app.tray = SimpleNamespace(set_interval=lambda minutes: None)
    app._refresh_tray_custom_reminders = lambda: None
    app._schedule_next_ambient_walk = lambda: None
    app._schedule_next_liveliness = lambda: None
    app._apply_schedule_visibility = lambda: None
    monkeypatch.setattr("daisy_pet.app.config.save", lambda cfg: None)

    app._apply_settings({**DEFAULTS, "memory_enabled": False})

    assert store.usage == [("2026-03-04", "code.exe", 60)]
    assert store.closed
    assert app.memory is None


def test_quit_flushes_and_closes_memory():
    store = _FakeMemory()
    app = DaisyApplication.__new__(DaisyApplication)
    app.memory = store
    app.usage = SimpleNamespace(flush=lambda: ("2026-03-04", "code.exe", 60))
    quits = []
    app.qt_app = SimpleNamespace(quit=lambda: quits.append(True))

    app.quit()

    assert store.usage == [("2026-03-04", "code.exe", 60)]
    assert store.closed
    assert quits == [True]
