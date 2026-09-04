from datetime import datetime
import random
from types import SimpleNamespace

from PySide6.QtCore import QPoint

from daisy_pet.activity import ActivitySnapshot, Observation, WindowInfo
from daisy_pet.app import DaisyApplication, SIP_DURATION_MS
from daisy_pet.liveliness import Behaviour
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
        "walk_crossing_seconds": 8,
        "walk_drink_fraction": 0.4,
    }
    app.pet = SimpleNamespace(
        isVisible=lambda: True,
        start_sip=lambda duration: events.append(("sip", duration)),
    )
    app.reminder = SimpleNamespace(mark_fired=lambda: events.append("fired"))
    app.walker = SimpleNamespace(
        reminder_walk_in=lambda crossing, fraction, callback: callback()
    )
    app._signals = lambda: None
    app._show_reminder_line = lambda line, tone, actionable: events.append(
        ("line", line, tone, actionable)
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
