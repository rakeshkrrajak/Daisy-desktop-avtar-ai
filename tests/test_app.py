from types import SimpleNamespace

from daisy_pet.app import DaisyApplication, SIP_DURATION_MS
from daisy_pet.mood import MoodDecision


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
