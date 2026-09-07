"""Local, offline memory of Daisy's day, stored in a small SQLite file.

Nothing here leaves the laptop and nothing plaintext derived from window or
tab titles is written: app usage is keyed by process name and tab decisions
by the same truncated SHA-256 hash the keep list uses.
"""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from .config import MAX_NOTE_TEXT_LENGTH, memory_path

SCHEMA_VERSION = 1
USAGE_MAX_GAP_SECONDS = 120
USAGE_FLUSH_SECONDS = 300
USAGE_IDLE_SECONDS = 300

HYDRATION_ACK = "hydration_ack"
HYDRATION_SNOOZE = "hydration_snooze"
HYDRATION_IGNORED = "hydration_ignored"
TAB_KEPT = "tab_kept"
TAB_CLOSED = "tab_closed"
HYDRATION_KINDS = (HYDRATION_ACK, HYDRATION_SNOOZE, HYDRATION_IGNORED)
TAB_KINDS = (TAB_KEPT, TAB_CLOSED)

_SCHEMA = (
    (
        "CREATE TABLE IF NOT EXISTS meta ("
        "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    ),
    (
        "CREATE TABLE IF NOT EXISTS app_usage ("
        "day TEXT NOT NULL, process TEXT NOT NULL, seconds INTEGER NOT NULL, "
        "PRIMARY KEY (day, process))"
    ),
    (
        "CREATE TABLE IF NOT EXISTS events ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, day TEXT NOT NULL, "
        "at TEXT NOT NULL, kind TEXT NOT NULL, detail TEXT)"
    ),
    (
        "CREATE TABLE IF NOT EXISTS notes ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, day TEXT NOT NULL, "
        "at TEXT NOT NULL, text TEXT NOT NULL, due_date TEXT)"
    ),
    "CREATE INDEX IF NOT EXISTS events_day ON events(day)",
    "CREATE INDEX IF NOT EXISTS notes_day ON notes(day)",
    "CREATE INDEX IF NOT EXISTS notes_due ON notes(due_date)",
)


@dataclass(frozen=True)
class Note:
    text: str
    due_date: str | None = None


@dataclass(frozen=True)
class DaySummary:
    day: str
    app_seconds: tuple[tuple[str, int], ...] = ()
    sips_acknowledged: int = 0
    sips_offered: int = 0
    tabs_kept: int = 0
    tabs_closed: int = 0
    notes: tuple[Note, ...] = ()
    notes_due: tuple[Note, ...] = ()

    @property
    def empty(self) -> bool:
        return not (
            self.app_seconds
            or self.sips_offered
            or self.tabs_kept
            or self.tabs_closed
            or self.notes
            or self.notes_due
        )


def title_hash(title: str) -> str:
    return hashlib.sha256(title.strip().lower().encode("utf-8")).hexdigest()[:16]


def valid_note_text(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value.strip())
        and len(value.strip()) <= MAX_NOTE_TEXT_LENGTH
    )


def _day(value: date | datetime) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    return value.isoformat()


class Memory:
    """Thin, failure-tolerant wrapper around the memory database."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def close(self) -> None:
        try:
            self._connection.close()
        except sqlite3.Error:
            pass

    def record_app_usage(self, day: date | str, process: str, seconds: int) -> None:
        if not process or seconds < 1:
            return
        stored_day = day if isinstance(day, str) else _day(day)
        self._write(
            "INSERT INTO app_usage (day, process, seconds) VALUES (?, ?, ?) "
            "ON CONFLICT(day, process) DO UPDATE SET "
            "seconds = seconds + excluded.seconds",
            (stored_day, process.lower(), int(seconds)),
        )

    def record_hydration(self, kind: str, at: datetime | None = None) -> None:
        if kind not in HYDRATION_KINDS:
            return
        self._record_event(kind, None, at)

    def record_tab_decision(
        self, kind: str, title: str, at: datetime | None = None
    ) -> None:
        if kind not in TAB_KINDS:
            return
        self._record_event(kind, title_hash(title), at)

    def add_note(
        self,
        text: str,
        due_date: date | str | None = None,
        at: datetime | None = None,
    ) -> bool:
        if not valid_note_text(text):
            return False
        moment = at or datetime.now()
        due = None if due_date is None else (
            due_date if isinstance(due_date, str) else _day(due_date)
        )
        return self._write(
            "INSERT INTO notes (day, at, text, due_date) VALUES (?, ?, ?, ?)",
            (_day(moment), moment.isoformat(), text.strip(), due),
        )

    def summary(self, day: date | str) -> DaySummary:
        stored_day = day if isinstance(day, str) else _day(day)
        usage = self._read(
            "SELECT process, seconds FROM app_usage WHERE day = ? "
            "ORDER BY seconds DESC, process ASC",
            (stored_day,),
        )
        counts = dict(
            self._read(
                "SELECT kind, COUNT(*) FROM events WHERE day = ? GROUP BY kind",
                (stored_day,),
            )
        )
        notes = self._read(
            "SELECT text, due_date FROM notes WHERE day = ? ORDER BY id ASC",
            (stored_day,),
        )
        notes_due = self._read(
            "SELECT text, due_date FROM notes WHERE due_date = ? ORDER BY id ASC",
            (stored_day,),
        )
        acknowledged = int(counts.get(HYDRATION_ACK, 0))
        offered = sum(int(counts.get(kind, 0)) for kind in HYDRATION_KINDS)
        return DaySummary(
            day=stored_day,
            app_seconds=tuple(
                (str(process), int(seconds)) for process, seconds in usage
            ),
            sips_acknowledged=acknowledged,
            sips_offered=offered,
            tabs_kept=int(counts.get(TAB_KEPT, 0)),
            tabs_closed=int(counts.get(TAB_CLOSED, 0)),
            notes=tuple(Note(str(text), due) for text, due in notes),
            notes_due=tuple(Note(str(text), due) for text, due in notes_due),
        )

    def prune(self, before: date | str) -> None:
        cutoff = before if isinstance(before, str) else _day(before)
        self._write("DELETE FROM app_usage WHERE day < ?", (cutoff,))
        self._write("DELETE FROM events WHERE day < ?", (cutoff,))
        self._write(
            "DELETE FROM notes WHERE day < ? AND (due_date IS NULL OR due_date < ?)",
            (cutoff, cutoff),
        )

    def _record_event(
        self, kind: str, detail: str | None, at: datetime | None
    ) -> None:
        moment = at or datetime.now()
        self._write(
            "INSERT INTO events (day, at, kind, detail) VALUES (?, ?, ?, ?)",
            (_day(moment), moment.isoformat(), kind, detail),
        )

    def _write(self, statement: str, parameters: tuple) -> bool:
        try:
            with self._connection:
                self._connection.execute(statement, parameters)
            return True
        except sqlite3.Error:
            return False

    def _read(self, statement: str, parameters: tuple) -> list[tuple]:
        try:
            return list(self._connection.execute(statement, parameters).fetchall())
        except sqlite3.Error:
            return []


class UsageAccumulator:
    """Turns 20-second activity polls into occasional per-app usage chunks.

    `observe` returns a (day, process, seconds) chunk whenever one is ready to
    be written, so a poll never becomes a database row of its own.
    """

    def __init__(
        self,
        max_gap_seconds: int = USAGE_MAX_GAP_SECONDS,
        flush_seconds: int = USAGE_FLUSH_SECONDS,
        idle_seconds: int = USAGE_IDLE_SECONDS,
    ) -> None:
        self.max_gap_seconds = max_gap_seconds
        self.flush_seconds = flush_seconds
        self.idle_seconds = idle_seconds
        self._process = ""
        self._day = ""
        self._at: datetime | None = None
        self._seconds = 0.0

    def observe(
        self, process: str, at: datetime, idle_seconds: float = 0.0
    ) -> tuple[str, str, int] | None:
        if not process or idle_seconds >= self.idle_seconds:
            chunk = self.flush()
            self._process = ""
            self._day = ""
            self._at = None
            return chunk
        day = _day(at)
        elapsed = None if self._at is None else (at - self._at).total_seconds()
        if (
            process != self._process
            or day != self._day
            or elapsed is None
            or not 0 <= elapsed <= self.max_gap_seconds
        ):
            chunk = self.flush()
            self._process = process
            self._day = day
            self._at = at
            return chunk
        self._seconds += elapsed
        self._at = at
        if self._seconds >= self.flush_seconds:
            return self.flush()
        return None

    def flush(self) -> tuple[str, str, int] | None:
        seconds = int(self._seconds)
        self._seconds = 0.0
        if not self._process or seconds < 1:
            return None
        return (self._day, self._process, seconds)


def _create_schema(connection: sqlite3.Connection) -> None:
    with connection:
        for statement in _SCHEMA:
            connection.execute(statement)
        connection.execute(
            "INSERT INTO meta (key, value) VALUES ('schema_version', ?) "
            "ON CONFLICT(key) DO NOTHING",
            (str(SCHEMA_VERSION),),
        )


def open_memory(path: Path | None = None) -> Memory | None:
    """Open (and create if needed) the memory database.

    A missing, unreadable or corrupt file degrades to no memory at all
    instead of taking the app down with it.
    """
    target = path or memory_path()
    connection = None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(target)
        _create_schema(connection)
        return Memory(connection)
    except (sqlite3.Error, OSError, ValueError):
        if connection is not None:
            try:
                connection.close()
            except sqlite3.Error:
                pass
        return None
