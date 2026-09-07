import random

from daisy_pet.lines import (
    EMPTY_SUMMARY_LINES,
    TEMPLATES,
    ack_line,
    app_label,
    day_summary_line,
    pick_line,
    tickle_line,
)
from daisy_pet.memory import DaySummary, Note


def test_seeded_lines_are_deterministic():
    assert pick_line("cheerful", random.Random(4)) == pick_line(
        "cheerful", random.Random(4)
    )
    assert ack_line(random.Random(4)) == ack_line(random.Random(4))


def test_unknown_tone_uses_playful_pool():
    assert pick_line("unknown", random.Random(2)) in TEMPLATES["playful"]


def test_tickle_line_uses_expected_pool():
    assert tickle_line(random.Random(2)) in {
        "Hehe — that tickles!",
        "Eee! Stop it, that tickles!",
        "Hehehe, okay okay, I'm awake!",
    }


def test_day_summary_line_on_a_realistic_day():
    summary = DaySummary(
        day="2026-03-04",
        app_seconds=(("code.exe", 4 * 3600), ("ms-teams.exe", 3600), ("x.exe", 30)),
        sips_acknowledged=5,
        sips_offered=8,
        tabs_kept=3,
        notes=(Note(text="call Manisha", due_date="2026-03-04"), Note(text="ship it")),
        notes_due=(Note(text="call Manisha", due_date="2026-03-04"),),
    )
    line = day_summary_line(summary, random.Random(1))
    assert line == (
        "Today: 4h in VS Code · 1h in Teams · 5 of 8 sips · 3 tabs kept · 2 notes"
        " — due today: call Manisha"
    )
    assert line == day_summary_line(summary, random.Random(1))


def test_day_summary_line_singular_counts_and_closed_tabs():
    summary = DaySummary(
        day="2026-03-04",
        tabs_kept=1,
        tabs_closed=1,
        notes=(Note(text="one thing"),),
    )
    assert day_summary_line(summary) == (
        "Today: 1 tab kept · 1 tab closed · 1 note"
    )


def test_day_summary_line_on_an_empty_day():
    line = day_summary_line(DaySummary(day="2026-03-04"), random.Random(3))
    assert line in EMPTY_SUMMARY_LINES


def test_day_summary_line_is_bounded_and_never_leaks_full_note_text():
    summary = DaySummary(
        day="2026-03-04",
        notes=tuple(Note(text="x" * 200) for _ in range(20)),
        notes_due=tuple(Note(text="y" * 200, due_date="2026-03-04") for _ in range(5)),
    )
    line = day_summary_line(summary)
    assert len(line) <= 220
    assert "y" * 60 not in line


def test_app_label_falls_back_to_the_process_stem():
    assert app_label("code.exe") == "VS Code"
    assert app_label("my-tool.exe") == "My Tool"
    assert app_label("") == "something"
