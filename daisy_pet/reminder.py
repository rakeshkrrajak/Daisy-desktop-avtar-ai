import random
import time
from dataclasses import dataclass, field
from typing import Callable


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
