from datetime import datetime, timedelta
import random
from types import SimpleNamespace

from PySide6.QtCore import QPoint, QRect, QSize

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
    app.mood_state = SimpleNamespace(
        record_ignored=lambda: events.append("ignored")
    )
    app._finish_reminder_walk = lambda: events.append("finish")
    app.bubble = SimpleNamespace(
        isVisible=lambda: False,
        show_message=lambda *args, **kwargs: events.append("message"),
    )
    app.pet = SimpleNamespace(geometry=lambda: QRect(10, 20, 50, 60))
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
    app.mood_state = SimpleNamespace(
        record_ignored=lambda: events.append("ignored")
    )
    app._finish_reminder_walk = lambda: events.append("finish")
    app.bubble = SimpleNamespace(
        isVisible=lambda: False,
        show_choice=lambda *args, **kwargs: events.append("prompt"),
    )
    app.pet = SimpleNamespace(geometry=lambda: QRect(10, 20, 50, 60))
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


def test_reminder_ack_choice_does_not_record_ignored(monkeypatch):
    events = []
    app = DaisyApplication.__new__(DaisyApplication)
    app.cfg = {"mood_enabled": True}
    app._reminder_choice_active = True
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
        sync=lambda snapshot: "closed",
    )
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


def test_review_bubble_uses_moved_to_anchor(monkeypatch):
    app = DaisyApplication.__new__(DaisyApplication)
    app.cfg = {"bubble_seconds": 12}
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
    app._reminder_choice_active = False
    app.tab_review = SimpleNamespace(active=False)
    app._tab_review_prompt = False
    app.mood_state = SimpleNamespace(record_ignored=lambda: setattr(
        app.mood_state, "ignored", True
    ))
    monkeypatch.setattr("daisy_pet.app.mood.save", lambda state: None)

    app._on_bubble_ignored()

    assert app.mood_state.ignored is True
