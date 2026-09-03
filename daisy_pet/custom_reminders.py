"""User-defined reminders (a task/message plus its own schedule), separate
from the built-in water reminder.

Each reminder fires either on a repeating interval or once a day at a fixed
clock time, and can be snoozed by its own configured duration.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from .reminder import TimeOfDayReminder, WaterReminder

MODE_INTERVAL = "interval"
MODE_TIME_OF_DAY = "time_of_day"
DEFAULT_SNOOZE_MINUTES = 10


def new_id() -> str:
    return uuid.uuid4().hex[:8]


@dataclass
class CustomReminder:
    reminder_id: str
    text: str
    mode: str = MODE_INTERVAL
    interval_minutes: int | None = None
    time_of_day: str | None = None
    snooze_minutes: int = DEFAULT_SNOOZE_MINUTES
    enabled: bool = True
    monotonic_clock: Callable[[], float] = time.monotonic
    wall_clock: Callable[[], datetime] = datetime.now
    engine: WaterReminder | TimeOfDayReminder = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("text must not be empty")
        if (
            not isinstance(self.snooze_minutes, int)
            or isinstance(self.snooze_minutes, bool)
            or self.snooze_minutes < 1
        ):
            raise ValueError("snooze_minutes must be an integer of at least 1")
        if self.mode == MODE_INTERVAL:
            if not self.interval_minutes:
                raise ValueError("interval_minutes is required in interval mode")
            self.engine = WaterReminder(self.interval_minutes, self.monotonic_clock)
        elif self.mode == MODE_TIME_OF_DAY:
            if not self.time_of_day:
                raise ValueError("time_of_day is required in time_of_day mode")
            self.engine = TimeOfDayReminder(self.time_of_day, self.wall_clock)
        else:
            raise ValueError(f"unknown mode: {self.mode!r}")

    def due(self) -> bool:
        return self.enabled and self.engine.due()

    def mark_fired(self) -> None:
        self.engine.mark_fired()

    def snooze(self, minutes: int | None = None) -> None:
        self.engine.snooze(minutes if minutes is not None else self.snooze_minutes)

    @property
    def seconds_remaining(self) -> float:
        return self.engine.seconds_remaining

    def summary(self) -> str:
        if self.mode == MODE_TIME_OF_DAY:
            return f"{self.text} — daily at {self.time_of_day}"
        return f"{self.text} — every {self.interval_minutes} min"

    def to_dict(self) -> dict:
        return {
            "id": self.reminder_id,
            "text": self.text,
            "mode": self.mode,
            "interval_minutes": self.interval_minutes,
            "time_of_day": self.time_of_day,
            "snooze_minutes": self.snooze_minutes,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict,
        monotonic_clock: Callable[[], float] = time.monotonic,
        wall_clock: Callable[[], datetime] = datetime.now,
    ) -> "CustomReminder":
        return cls(
            reminder_id=data["id"],
            text=data["text"],
            mode=data.get("mode", MODE_INTERVAL),
            interval_minutes=data.get("interval_minutes"),
            time_of_day=data.get("time_of_day"),
            snooze_minutes=data.get("snooze_minutes", DEFAULT_SNOOZE_MINUTES),
            enabled=data.get("enabled", True),
            monotonic_clock=monotonic_clock,
            wall_clock=wall_clock,
        )


class CustomReminderStore:
    """Holds the full set of user-defined reminders."""

    def __init__(self, items: list[CustomReminder] | None = None) -> None:
        self.items: list[CustomReminder] = list(items) if items else []

    def add(
        self,
        text: str,
        *,
        mode: str = MODE_INTERVAL,
        interval_minutes: int | None = None,
        time_of_day: str | None = None,
        snooze_minutes: int = DEFAULT_SNOOZE_MINUTES,
        enabled: bool = True,
        monotonic_clock: Callable[[], float] = time.monotonic,
        wall_clock: Callable[[], datetime] = datetime.now,
    ) -> CustomReminder:
        item = CustomReminder(
            reminder_id=new_id(),
            text=text,
            mode=mode,
            interval_minutes=interval_minutes,
            time_of_day=time_of_day,
            snooze_minutes=snooze_minutes,
            enabled=enabled,
            monotonic_clock=monotonic_clock,
            wall_clock=wall_clock,
        )
        self.items.append(item)
        return item

    def remove(self, reminder_id: str) -> None:
        self.items = [i for i in self.items if i.reminder_id != reminder_id]

    def find(self, reminder_id: str) -> CustomReminder | None:
        for item in self.items:
            if item.reminder_id == reminder_id:
                return item
        return None

    def due_items(self) -> list[CustomReminder]:
        return [i for i in self.items if i.due()]

    def to_config_list(self) -> list[dict]:
        return [i.to_dict() for i in self.items]

    @classmethod
    def from_config_list(
        cls,
        data: list[dict],
        monotonic_clock: Callable[[], float] = time.monotonic,
        wall_clock: Callable[[], datetime] = datetime.now,
    ) -> "CustomReminderStore":
        return cls(
            [
                CustomReminder.from_dict(d, monotonic_clock, wall_clock)
                for d in data
            ]
        )
