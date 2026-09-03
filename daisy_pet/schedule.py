"""Helpers for checking whether Daisy is inside her configured active hours."""

from __future__ import annotations

import re
from datetime import datetime, time as dtime

_TIME_RE = re.compile(r"^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$")


def is_valid_time_string(value: object) -> bool:
    return isinstance(value, str) and bool(_TIME_RE.match(value))


def parse_time(value: str) -> dtime:
    if not is_valid_time_string(value):
        raise ValueError(f"invalid HH:MM time string: {value!r}")
    hours, minutes = value.split(":")
    return dtime(int(hours), int(minutes))


def is_active(start: str, end: str, now: datetime | None = None) -> bool:
    """Return True if `now` falls within the [start, end) window.

    Supports overnight windows where `end` is earlier than `start` (for
    example "22:00" to "06:00"). A window where start == end is treated as
    always active.
    """
    moment = (now or datetime.now()).time()
    start_t = parse_time(start)
    end_t = parse_time(end)
    if start_t == end_t:
        return True
    if start_t < end_t:
        return start_t <= moment < end_t
    return moment >= start_t or moment < end_t
