"""User-defined reminders (a task/message plus its own interval), separate
from the built-in water reminder.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Callable

from .reminder import WaterReminder


def new_id() -> str:
    return uuid.uuid4().hex[:8]


@dataclass
class CustomReminder:
    reminder_id: str
    text: str
    interval_minutes: int
    enabled: bool = True
    clock: Callable[[], float] = time.monotonic
    engine: WaterReminder = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("text must not be empty")
        self.engine = WaterReminder(self.interval_minutes, self.clock)

    def due(self) -> bool:
        return self.enabled and self.engine.due()

    def mark_fired(self) -> None:
        self.engine.mark_fired()

    def set_interval(self, minutes: int) -> None:
        self.engine.set_interval(minutes)
        self.interval_minutes = minutes

    def to_dict(self) -> dict:
        return {
            "id": self.reminder_id,
            "text": self.text,
            "interval_minutes": self.interval_minutes,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(
        cls, data: dict, clock: Callable[[], float] = time.monotonic
    ) -> "CustomReminder":
        return cls(
            reminder_id=data["id"],
            text=data["text"],
            interval_minutes=data["interval_minutes"],
            enabled=data.get("enabled", True),
            clock=clock,
        )


class CustomReminderStore:
    """Holds the full set of user-defined reminders."""

    def __init__(self, items: list[CustomReminder] | None = None) -> None:
        self.items: list[CustomReminder] = list(items) if items else []

    def add(
        self,
        text: str,
        interval_minutes: int,
        enabled: bool = True,
        clock: Callable[[], float] = time.monotonic,
    ) -> CustomReminder:
        item = CustomReminder(new_id(), text, interval_minutes, enabled, clock)
        self.items.append(item)
        return item

    def remove(self, reminder_id: str) -> None:
        self.items = [i for i in self.items if i.reminder_id != reminder_id]

    def due_items(self) -> list[CustomReminder]:
        return [i for i in self.items if i.due()]

    def to_config_list(self) -> list[dict]:
        return [i.to_dict() for i in self.items]

    @classmethod
    def from_config_list(
        cls, data: list[dict], clock: Callable[[], float] = time.monotonic
    ) -> "CustomReminderStore":
        return cls([CustomReminder.from_dict(d, clock) for d in data])
