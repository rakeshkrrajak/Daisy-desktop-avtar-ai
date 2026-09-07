import sqlite3
from datetime import date, datetime, timedelta

from daisy_pet import memory


def _open(tmp_path):
    store = memory.open_memory(tmp_path / "memory.sqlite3")
    assert store is not None
    return store


def test_schema_is_created_on_first_use(tmp_path):
    path = tmp_path / "nested" / "memory.sqlite3"
    store = memory.open_memory(path)
    assert store is not None
    connection = sqlite3.connect(path)
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    version = connection.execute(
        "SELECT value FROM meta WHERE key = 'schema_version'"
    ).fetchone()
    connection.close()
    store.close()
    assert {"meta", "app_usage", "events", "notes"} <= tables
    assert version == (str(memory.SCHEMA_VERSION),)


def test_reopening_an_existing_database_keeps_rows(tmp_path):
    path = tmp_path / "memory.sqlite3"
    first = memory.open_memory(path)
    assert first is not None
    first.record_app_usage(date(2026, 3, 4), "code.exe", 600)
    first.close()
    second = memory.open_memory(path)
    assert second is not None
    assert second.summary(date(2026, 3, 4)).app_seconds == (("code.exe", 600),)
    second.close()


def test_corrupt_database_degrades_to_no_memory(tmp_path):
    path = tmp_path / "memory.sqlite3"
    path.write_bytes(b"this is not a database at all" * 10)
    assert memory.open_memory(path) is None


def test_unusable_path_degrades_to_no_memory(tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory", encoding="utf-8")
    assert memory.open_memory(blocker / "memory.sqlite3") is None


def test_app_usage_is_aggregated_per_day_and_process(tmp_path):
    store = _open(tmp_path)
    store.record_app_usage("2026-03-04", "code.exe", 600)
    store.record_app_usage("2026-03-04", "CODE.EXE", 300)
    store.record_app_usage("2026-03-04", "teams.exe", 120)
    store.record_app_usage("2026-03-05", "code.exe", 60)
    summary = store.summary("2026-03-04")
    store.close()
    assert summary.app_seconds == (("code.exe", 900), ("teams.exe", 120))


def test_app_usage_ignores_empty_process_and_sub_second_chunks(tmp_path):
    store = _open(tmp_path)
    store.record_app_usage("2026-03-04", "", 600)
    store.record_app_usage("2026-03-04", "code.exe", 0)
    summary = store.summary("2026-03-04")
    store.close()
    assert summary.app_seconds == ()


def test_summary_counts_hydration_tabs_and_notes(tmp_path):
    store = _open(tmp_path)
    at = datetime(2026, 3, 4, 9, 30)
    for kind in (
        memory.HYDRATION_ACK,
        memory.HYDRATION_ACK,
        memory.HYDRATION_SNOOZE,
        memory.HYDRATION_IGNORED,
    ):
        store.record_hydration(kind, at)
    store.record_tab_decision(memory.TAB_KEPT, "Some Long Article", at)
    store.record_tab_decision(memory.TAB_CLOSED, "Another Tab", at)
    store.add_note("call Manisha", date(2026, 3, 4), at)
    store.add_note("decided X with Bhavana", None, at)
    summary = store.summary(date(2026, 3, 4))
    store.close()
    assert summary.sips_acknowledged == 2
    assert summary.sips_offered == 4
    assert summary.tabs_kept == 1
    assert summary.tabs_closed == 1
    assert [note.text for note in summary.notes] == [
        "call Manisha",
        "decided X with Bhavana",
    ]
    assert [note.text for note in summary.notes_due] == ["call Manisha"]
    assert not summary.empty


def test_unknown_event_kinds_are_ignored(tmp_path):
    store = _open(tmp_path)
    at = datetime(2026, 3, 4, 9, 30)
    store.record_hydration("hydration_maybe", at)
    store.record_tab_decision("tab_burned", "Tab", at)
    summary = store.summary(date(2026, 3, 4))
    store.close()
    assert summary.empty


def test_tab_decisions_store_a_hash_not_the_title(tmp_path):
    path = tmp_path / "memory.sqlite3"
    store = memory.open_memory(path)
    assert store is not None
    store.record_tab_decision(
        memory.TAB_KEPT, "Quarterly Budget.xlsx", datetime(2026, 3, 4, 9, 0)
    )
    store.close()
    connection = sqlite3.connect(path)
    detail = connection.execute("SELECT detail FROM events").fetchone()[0]
    connection.close()
    assert detail == memory.title_hash("Quarterly Budget.xlsx")
    assert len(detail) == 16
    assert "budget" not in detail.lower()


def test_title_hash_normalizes_case_and_padding():
    assert memory.title_hash("  Some Tab  ") == memory.title_hash("some tab")


def test_note_text_is_validated_and_bounded(tmp_path):
    store = _open(tmp_path)
    at = datetime(2026, 3, 4, 9, 0)
    assert store.add_note("  call Manisha  ", None, at) is True
    assert store.add_note("   ", None, at) is False
    assert store.add_note("x" * 201, None, at) is False
    assert store.add_note("x" * 200, None, at) is True
    summary = store.summary(date(2026, 3, 4))
    store.close()
    assert summary.notes[0].text == "call Manisha"
    assert len(summary.notes) == 2


def test_valid_note_text_rejects_non_strings():
    assert not memory.valid_note_text(None)
    assert not memory.valid_note_text(12)
    assert memory.valid_note_text("hello")


def test_empty_day_summary(tmp_path):
    store = _open(tmp_path)
    summary = store.summary(date(2026, 3, 4))
    store.close()
    assert summary.empty
    assert summary.app_seconds == ()
    assert summary.notes == ()


def test_prune_drops_old_rows_but_keeps_future_due_notes(tmp_path):
    store = _open(tmp_path)
    old = datetime(2026, 3, 1, 9, 0)
    recent = datetime(2026, 3, 10, 9, 0)
    store.record_app_usage(old.date(), "code.exe", 600)
    store.record_app_usage(recent.date(), "code.exe", 60)
    store.record_hydration(memory.HYDRATION_ACK, old)
    store.record_hydration(memory.HYDRATION_ACK, recent)
    store.add_note("old note", None, old)
    store.add_note("old note with future due date", date(2026, 3, 20), old)
    store.prune(date(2026, 3, 5))
    old_day = store.summary(old.date())
    recent_day = store.summary(recent.date())
    future_day = store.summary(date(2026, 3, 20))
    store.close()
    assert old_day.app_seconds == ()
    assert old_day.sips_offered == 0
    assert [note.text for note in old_day.notes] == [
        "old note with future due date"
    ]
    assert recent_day.app_seconds == (("code.exe", 60),)
    assert recent_day.sips_acknowledged == 1
    assert [note.text for note in future_day.notes_due] == [
        "old note with future due date"
    ]


def test_writes_after_close_do_not_raise(tmp_path):
    store = _open(tmp_path)
    store.close()
    store.record_app_usage(date(2026, 3, 4), "code.exe", 60)
    store.record_hydration(memory.HYDRATION_ACK)
    assert store.add_note("note") is False
    assert store.summary(date(2026, 3, 4)).empty


def test_usage_accumulator_flushes_on_app_switch():
    accumulator = memory.UsageAccumulator()
    start = datetime(2026, 3, 4, 9, 0)
    assert accumulator.observe("code.exe", start) is None
    assert accumulator.observe("code.exe", start + timedelta(seconds=20)) is None
    assert accumulator.observe("code.exe", start + timedelta(seconds=40)) is None
    chunk = accumulator.observe("teams.exe", start + timedelta(seconds=60))
    assert chunk == ("2026-03-04", "code.exe", 40)


def test_usage_accumulator_flushes_when_the_chunk_gets_long():
    accumulator = memory.UsageAccumulator()
    start = datetime(2026, 3, 4, 9, 0)
    accumulator.observe("code.exe", start)
    chunks = [
        accumulator.observe("code.exe", start + timedelta(seconds=20 * step))
        for step in range(1, 17)
    ]
    written = [chunk for chunk in chunks if chunk is not None]
    assert written == [("2026-03-04", "code.exe", 300)]


def test_usage_accumulator_caps_long_gaps_and_skips_idle():
    accumulator = memory.UsageAccumulator()
    start = datetime(2026, 3, 4, 9, 0)
    accumulator.observe("code.exe", start)
    assert accumulator.observe("code.exe", start + timedelta(hours=3)) is None
    accumulator.observe("code.exe", start + timedelta(hours=3, seconds=20))
    chunk = accumulator.observe(
        "code.exe", start + timedelta(hours=3, seconds=40), idle_seconds=600
    )
    assert chunk == ("2026-03-04", "code.exe", 20)
    assert accumulator.flush() is None


def test_usage_accumulator_splits_across_midnight():
    accumulator = memory.UsageAccumulator()
    before = datetime(2026, 3, 4, 23, 59, 50)
    accumulator.observe("code.exe", before)
    accumulator.observe("code.exe", before + timedelta(seconds=5))
    chunk = accumulator.observe("code.exe", before + timedelta(seconds=15))
    assert chunk == ("2026-03-04", "code.exe", 5)
    assert accumulator.flush() is None
