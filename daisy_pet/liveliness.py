"""Seedable, pose-only idle behaviours for Daisy."""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Behaviour:
    name: str
    preferred: str
    fallback: str
    loops: int
    chatter: bool


_NIGHT = (
    (Behaviour("yawn", "sleepy", "waiting", 1, False), 4),
    (Behaviour("quiet_thought", "thinking", "review", 1, True), 2),
    (Behaviour("sleepy_glance", "sleepy", "waiting", 1, False), 3),
)
_BRIGHT = (
    (Behaviour("morning_wave", "happy", "waving", 1, True), 3),
    (Behaviour("sunny_hop", "happy", "jumping", 1, False), 3),
    (Behaviour("bright_wave", "happy", "waving", 2, False), 2),
)
_WORKING = (
    (Behaviour("thinking", "thinking", "review", 1, False), 4),
    (Behaviour("judging_glance", "judging", "waiting", 1, True), 2),
    (Behaviour("stretch", "surprised", "jumping", 1, False), 2),
    (Behaviour("work_wave", "happy", "waving", 1, False), 1),
)
_WINDING_DOWN = (
    (Behaviour("idle_glance", "happy", "idle", 1, True), 3),
    (Behaviour("evening_hop", "happy", "jumping", 1, False), 2),
    (Behaviour("evening_sleepy", "sleepy", "waiting", 1, False), 3),
)


def _bucket(hour: int) -> tuple[tuple[Behaviour, int], ...]:
    if hour >= 22 or hour < 6:
        return _NIGHT
    if hour < 11:
        return _BRIGHT
    if hour < 18:
        return _WORKING
    return _WINDING_DOWN


def pick(hour: int, rng: random.Random, last_name: str | None) -> Behaviour:
    if not 0 <= hour <= 23:
        raise ValueError("hour must be between 0 and 23")
    choices = _bucket(hour)
    if last_name is not None:
        choices = tuple(item for item in choices if item[0].name != last_name)
    behaviours = [item[0] for item in choices]
    weights = [item[1] for item in choices]
    return rng.choices(behaviours, weights=weights, k=1)[0]


def next_delay_seconds(
    rng: random.Random, min_seconds: int, max_seconds: int
) -> int:
    minimum = max(0, min_seconds)
    maximum = max(minimum, max_seconds)
    return rng.randint(minimum, maximum)
