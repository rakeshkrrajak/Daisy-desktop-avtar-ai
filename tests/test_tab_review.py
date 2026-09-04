import hashlib
import json
from datetime import date

import daisy_pet.tabs as tabs
from daisy_pet.tab_review import KeepList, TabReview


def tab(key: str, title: str) -> tabs.TabInfo:
    return tabs.TabInfo(key, title, "chrome.exe", False, 1)


def test_keep_list_expires_and_stores_only_hashed_titles(tmp_path):
    path = tmp_path / "tab_keeps.json"
    keeps = KeepList(path)
    today = date(2025, 1, 1)
    title = "Private project notes"
    keeps.keep(title, today)

    raw = path.read_text(encoding="utf-8")
    assert title not in raw
    key = hashlib.sha256(title.strip().lower().encode()).hexdigest()[:16]
    assert json.loads(raw) == {key: "2025-01-01"}
    assert keeps.is_kept(title, today)
    assert not keeps.is_kept(title, date(2025, 1, 2))
    assert json.loads(path.read_text(encoding="utf-8")) == {}


def test_keep_list_tolerates_corrupt_state(tmp_path):
    path = tmp_path / "tab_keeps.json"
    path.write_text("{nope", encoding="utf-8")
    assert not KeepList(path).is_kept("Anything", date(2025, 1, 1))


def test_review_skips_kept_titles_and_syncs_queue(tmp_path):
    today = date(2025, 1, 1)
    keeps = KeepList(tmp_path / "tab_keeps.json")
    keeps.keep("Keep this", today)
    first = tab("1:first", "Keep this")
    second = tab("2:second", "Review this")
    review = TabReview(keeps, today)
    review.start([first, second])
    assert review.active
    assert review.current() == second
    snapshot = tabs.TabSnapshot((second,), date(2025, 1, 1), "windows")
    assert review.sync(snapshot) == "waiting"
    assert review.sync(tabs.TabSnapshot((), today, "windows")) == "closed"
    assert review.sync(snapshot) == "done"


def test_review_keep_skip_and_cancel(tmp_path):
    today = date(2025, 1, 1)
    first = tab("1:first", "First")
    second = tab("2:second", "Second")
    review = TabReview(KeepList(tmp_path / "tab_keeps.json"), today)
    review.start([first, second])
    review.keep_current(today)
    assert review.current() == second
    assert review.keeps.is_kept("First", today)
    review.skip_current()
    assert not review.active
    review.start([first])
    review.cancel()
    assert review.current() is None


def test_focus_tab_returns_false_off_windows(monkeypatch):
    monkeypatch.setattr(tabs.sys, "platform", "linux")
    assert tabs.focus_tab("1:Anything") is False
