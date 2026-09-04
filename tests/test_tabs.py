from datetime import datetime, timedelta
import random

import daisy_pet.tabs as tabs


def snapshot(at, entries):
    return tabs.TabSnapshot(
        tuple(tabs.TabInfo(*entry) for entry in entries),
        at,
        "windows",
    )


def test_stale_boundary_and_active_refresh():
    start = datetime(2025, 1, 1, 9)
    watcher = tabs.TabWatcher(idle_minutes=60, min_open=1)
    entry = ("1:Docs", "Docs", "chrome.exe", False)
    assert watcher.observe(snapshot(start, [entry])) is None
    assert watcher.observe(snapshot(start + timedelta(minutes=59), [entry])) is None
    assert watcher.observe(snapshot(start + timedelta(minutes=60), [entry]))

    watcher = tabs.TabWatcher(idle_minutes=60, min_open=1)
    active = ("1:Docs", "Docs", "chrome.exe", True)
    watcher.observe(snapshot(start, [active]))
    assert watcher.observe(snapshot(start + timedelta(minutes=59), [active])) is None
    inactive = ("1:Docs", "Docs", "chrome.exe", False)
    assert watcher.observe(snapshot(start + timedelta(minutes=118), [inactive])) is None


def test_closed_tabs_are_pruned_and_never_mentioned():
    start = datetime(2025, 1, 1, 9)
    watcher = tabs.TabWatcher(idle_minutes=1, min_open=1)
    closed = ("1:Closed", "Closed", "chrome.exe", False)
    current = ("2:Current", "Current", "chrome.exe", True)
    watcher.observe(snapshot(start, [closed, current]))
    assert watcher.observe(
        snapshot(start + timedelta(minutes=2), [current])
    ) is None
    assert "1:Closed" not in watcher.last_active


def test_min_open_cooldown_and_per_tab_repeat_suppression():
    start = datetime(2025, 1, 1, 9)
    entries = [
        (str(index), f"Tab {index}", "chrome.exe", False)
        for index in range(8)
    ]
    watcher = tabs.TabWatcher(
        idle_minutes=1,
        min_open=8,
        cooldown_minutes=30,
        repeat_minutes=120,
        rng=random.Random(2),
    )
    assert watcher.observe(snapshot(start, entries)) is None
    first = watcher.observe(snapshot(start + timedelta(minutes=1), entries))
    assert first is not None
    assert watcher.observe(snapshot(start + timedelta(minutes=2), entries)) is None
    more = entries + [("8", "New", "chrome.exe", False)]
    assert watcher.observe(snapshot(start + timedelta(minutes=30), more)) is None
    assert watcher.observe(snapshot(start + timedelta(minutes=121), more))


def test_stale_line_collapses_truncates_and_caps_titles():
    long_title = "  " + ("word \n" * 45) + " "
    line = tabs.stale_tab_line(
        [long_title, "Second title", "Third title"],
        1,
        random.Random(3),
    )
    assert len(line) <= 220
    assert line.count('"') == 4
    assert "  " not in line
    assert "…" in line
    assert len(long_title.split()) > 40


def test_probe_tabs_returns_none_off_windows(monkeypatch):
    monkeypatch.setattr(tabs.sys, "platform", "linux")
    assert tabs.probe_tabs() is None
