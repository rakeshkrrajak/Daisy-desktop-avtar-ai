from datetime import datetime

import pytest

from daisy_pet.mood import MoodSignals, MoodState, decide, load, save


def signals(**kwargs):
    values = {
        "hour": 12,
        "minutes_since_ack": 10,
        "snooze_streak": 0,
        "ignored_streak": 0,
    }
    values.update(kwargs)
    return MoodSignals(**values)


def test_decision_priority_order():
    assert decide(signals(just_dragged=True, just_acknowledged=True)).mood == "surprised"
    assert decide(signals(just_acknowledged=True, just_snoozed=True)).mood == "happy"
    assert decide(signals(just_snoozed=True, snooze_streak=2)).mood == "disappointed"
    assert decide(signals(just_snoozed=True)).mood == "thinking"
    assert decide(signals(ignored_streak=2)).mood == "waiting"
    assert decide(signals(hour=23)).mood == "sleepy"
    assert decide(signals(first_appearance_today=True)).mood == "content"
    assert decide(signals(minutes_since_ack=None)).mood == "waiting"
    assert decide(signals()).mood == "neutral"


def test_decision_validates_signals():
    with pytest.raises(ValueError):
        decide(signals(hour=24))
    with pytest.raises(ValueError):
        decide(signals(snooze_streak=-1))
    with pytest.raises(ValueError):
        decide(signals(ignored_streak=-1))


def test_mood_state_roundtrip_and_helpers(tmp_path):
    path = tmp_path / "mood_state.json"
    state = MoodState()
    assert state.mark_seen("2025-01-01")
    assert not state.mark_seen("2025-01-01")
    state.record_snooze()
    state.record_snooze()
    state.record_ignored()
    state.record_ack(datetime(2025, 1, 1, 12, 0))
    save(state, path)
    assert load(path) == state
    assert state.snooze_streak == 0
    assert state.ignored_streak == 0


def test_mood_state_corrupt_falls_back(tmp_path):
    path = tmp_path / "mood_state.json"
    path.write_text("{bad", encoding="utf-8")
    assert load(path) == MoodState()
