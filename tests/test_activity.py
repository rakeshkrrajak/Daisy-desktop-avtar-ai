from datetime import datetime, timedelta
import random
from types import SimpleNamespace

import daisy_pet.activity as activity
from daisy_pet.activity import (
    ActivitySnapshot,
    ActivityWatcher,
    WindowInfo,
    probe,
)
from daisy_pet.lines import OBSERVATION_LINES, pick_observation


def snapshot(
    at,
    *,
    title="Editor",
    process="code.exe",
    idle=0,
    browsers=0,
):
    return ActivitySnapshot(
        WindowInfo(title, process),
        idle,
        browsers,
        at,
    )


def test_observation_rules_follow_priority_order():
    start = datetime(2025, 1, 1, 9)
    watcher = ActivityWatcher()
    assert watcher.observe(
        snapshot(start, title="Microsoft Teams — Meeting", browsers=7)
    ).kind == "meeting"

    watcher = ActivityWatcher()
    assert watcher.observe(snapshot(start, title="Chat | Alice")).kind == "message"

    watcher = ActivityWatcher()
    assert watcher.observe(snapshot(start, browsers=7)).kind == "browser_sprawl"

    watcher = ActivityWatcher()
    assert watcher.observe(snapshot(start, process="code.exe")) is None
    assert watcher.observe(
        snapshot(start + timedelta(minutes=45), process="code.exe")
    ).kind == "long_focus"

    watcher = ActivityWatcher()
    assert watcher.observe(snapshot(start, idle=600)) is None
    assert watcher.observe(snapshot(start + timedelta(minutes=1), idle=0)).kind == (
        "idle_return"
    )

    watcher = ActivityWatcher(focus_minutes=120)
    assert watcher.observe(snapshot(start)) is None
    assert watcher.observe(
        snapshot(start + timedelta(minutes=90))
    ).kind == "sitting"


def test_observation_cooldown_suppresses_same_kind():
    start = datetime(2025, 1, 1, 9)
    watcher = ActivityWatcher()
    assert watcher.observe(snapshot(start, browsers=7)).kind == "browser_sprawl"
    assert watcher.observe(
        snapshot(start + timedelta(minutes=19), browsers=7)
    ) is None
    assert watcher.observe(
        snapshot(start + timedelta(minutes=20), browsers=7)
    ).kind == "browser_sprawl"


def test_probe_returns_none_off_windows(monkeypatch):
    monkeypatch.setattr(activity.sys, "platform", "linux")
    assert probe() is None


def test_probe_ctypes_failure_returns_safe_snapshot(monkeypatch):
    class Broken:
        def __getattr__(self, name):
            raise OSError(name)

    monkeypatch.setattr(activity.sys, "platform", "win32")
    monkeypatch.setattr(
        activity.ctypes,
        "windll",
        SimpleNamespace(user32=Broken(), kernel32=Broken()),
        raising=False,
    )
    result = probe()
    assert result is not None
    assert result.window == WindowInfo("", "")
    assert result.idle_seconds == 0
    assert result.browser_window_count == 0


def test_observation_lines_are_deterministic_with_rng():
    for kind, lines in OBSERVATION_LINES.items():
        assert pick_observation(kind, random.Random(4)) in lines
        assert pick_observation(kind, random.Random(4)) == pick_observation(
            kind, random.Random(4)
        )
