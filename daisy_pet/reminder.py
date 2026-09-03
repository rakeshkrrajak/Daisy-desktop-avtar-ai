import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable

from . import schedule


@dataclass
class WaterReminder:
    interval_minutes: int
    clock: Callable[[], float] = time.monotonic
    _next_due: float = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._validate_minutes(self.interval_minutes)
        self._next_due = self.clock() + self.interval_minutes * 60

    @staticmethod
    def _validate_minutes(minutes: int) -> None:
        if not isinstance(minutes, int) or isinstance(minutes, bool) or minutes < 1:
            raise ValueError("minutes must be an integer of at least 1")

    @property
    def seconds_remaining(self) -> float:
        return max(0.0, self._next_due - self.clock())

    def due(self) -> bool:
        return self.clock() >= self._next_due

    def mark_fired(self) -> None:
        self._next_due = self.clock() + self.interval_minutes * 60

    def snooze(self, minutes: int) -> None:
        self._validate_minutes(minutes)
        self._next_due = self.clock() + minutes * 60

    def set_interval(self, minutes: int) -> None:
        self._validate_minutes(minutes)
        self.interval_minutes = minutes
        self._next_due = self.clock() + minutes * 60


@dataclass
class TimeOfDayReminder:
    """Fires once a day at a fixed clock time (e.g. "15:00"), then rolls
    over to the same time the next day.
    """

    time_of_day: str
    clock: Callable[[], datetime] = datetime.now
    _next_due: datetime = field(init=False, repr=False)

    def __post_init__(self) -> None:
        schedule.parse_time(self.time_of_day)  # raises if malformed
        self._next_due = self._compute_next(self.clock())

    def _compute_next(self, now: datetime) -> datetime:
        target = schedule.parse_time(self.time_of_day)
        candidate = now.replace(
            hour=target.hour, minute=target.minute, second=0, microsecond=0
        )
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate

    @property
    def seconds_remaining(self) -> float:
        return max(0.0, (self._next_due - self.clock()).total_seconds())

    def due(self) -> bool:
        return self.clock() >= self._next_due

    def mark_fired(self) -> None:
        self._next_due = self._compute_next(self.clock())

    def snooze(self, minutes: int) -> None:
        if not isinstance(minutes, int) or isinstance(minutes, bool) or minutes < 1:
            raise ValueError("minutes must be an integer of at least 1")
        self._next_due = self.clock() + timedelta(minutes=minutes)

    def set_time_of_day(self, value: str) -> None:
        schedule.parse_time(value)
        self.time_of_day = value
        self._next_due = self._compute_next(self.clock())


MESSAGES = (
    "Hydration station! Your body called.",
    "Tiny sip, big productivity.",
    "Drink some water, superstar.",
    "Daisy says: time for a refreshing sip.",
    "Your future self would love a glass of water.",
    "A little water break never hurt.",
    "Sip happens. Make it a good one.",
    "Keep calm and hydrate on.",
)


def pick_message(rng: random.Random | None = None) -> str:
    chooser = rng or random
    return chooser.choice(MESSAGES)
