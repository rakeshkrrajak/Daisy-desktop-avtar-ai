"""Private, deterministic state for the stale-tab review walkthrough."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from .config import mood_state_path
from .tabs import TabInfo, TabSnapshot


def tab_keeps_path() -> Path:
    return mood_state_path().with_name("tab_keeps.json")


class KeepList:
    def __init__(self, path: Path | None = None, today: date | None = None) -> None:
        self.path = path or tab_keeps_path()
        self._entries: dict[str, str] = {}
        self._load()
        if today is not None:
            self.prune(today)

    @staticmethod
    def _key(title: str) -> str:
        normalized = title.strip().lower().encode("utf-8")
        return hashlib.sha256(normalized).hexdigest()[:16]

    def _load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return
            self._entries = {
                str(key): value
                for key, value in raw.items()
                if isinstance(key, str)
                and len(key) == 16
                and isinstance(value, str)
            }
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            self._entries = {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f"{self.path.name}.tmp")
        temporary.write_text(
            json.dumps(self._entries, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def keep(self, title: str, today: date) -> None:
        self.prune(today, save=False)
        self._entries[self._key(title)] = today.isoformat()
        self._save()

    def is_kept(self, title: str, today: date) -> bool:
        self.prune(today)
        return self._entries.get(self._key(title)) == today.isoformat()

    def prune(self, today: date, save: bool = True) -> None:
        value = today.isoformat()
        original = len(self._entries)
        self._entries = {
            key: stored for key, stored in self._entries.items() if stored == value
        }
        if save and len(self._entries) != original:
            self._save()


class TabReview:
    def __init__(
        self,
        keeps: KeepList | None = None,
        today: date | None = None,
    ) -> None:
        self.keeps = keeps or KeepList()
        self.today = today
        self._queue: list[TabInfo] = []

    @property
    def active(self) -> bool:
        return bool(self._queue)

    def start(self, tabs: tuple[TabInfo, ...] | list[TabInfo]) -> None:
        if self.today is None:
            self._queue = list(tabs)
        else:
            self._queue = [
                tab for tab in tabs if not self.keeps.is_kept(tab.title, self.today)
            ]

    def current(self) -> TabInfo | None:
        return self._queue[0] if self._queue else None

    def keep_current(self, today: date) -> None:
        current = self.current()
        if current is not None:
            self.keeps.keep(current.title, today)
            self._queue.pop(0)

    def skip_current(self) -> None:
        if self._queue:
            self._queue.pop(0)

    def sync(self, snapshot: TabSnapshot) -> str:
        current = self.current()
        if current is None:
            return "done"
        if current.key not in {tab.key for tab in snapshot.tabs}:
            self._queue.pop(0)
            return "closed"
        return "waiting"

    def cancel(self) -> None:
        self._queue.clear()
