import copy
import json
import os
import sys
from pathlib import Path
from typing import Any

from . import schedule


DEFAULTS = {
    "interval_minutes": 30,
    "bubble_seconds": 12,
    "scale": 1.0,
    "pos": None,
    "enabled": True,
    "walk_enabled": True,
    "ambient_walk_min_minutes": 3,
    "ambient_walk_max_minutes": 8,
    "walk_crossing_seconds": 8,
    "walk_drink_fraction": 0.4,
    "schedule_enabled": False,
    "schedule_start": "08:00",
    "schedule_end": "22:00",
    "custom_reminders": [],
}

MAX_CUSTOM_REMINDER_TEXT_LENGTH = 200


def _valid_minutes(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def _valid_custom_reminders(value: Any) -> bool:
    if not isinstance(value, list):
        return False
    for item in value:
        if not isinstance(item, dict):
            return False
        reminder_id, text, enabled = (
            item.get("id"),
            item.get("text"),
            item.get("enabled"),
        )
        mode = item.get("mode", "interval")
        snooze_minutes = item.get("snooze_minutes", 10)
        if not isinstance(reminder_id, str) or not reminder_id:
            return False
        if (
            not isinstance(text, str)
            or not text.strip()
            or len(text) > MAX_CUSTOM_REMINDER_TEXT_LENGTH
        ):
            return False
        if not isinstance(enabled, bool):
            return False
        if not _valid_minutes(snooze_minutes):
            return False
        if mode == "interval":
            if not _valid_minutes(item.get("interval_minutes")):
                return False
        elif mode == "time_of_day":
            if not schedule.is_valid_time_string(item.get("time_of_day")):
                return False
        else:
            return False
    return True


def config_path() -> Path:
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "DenimDaisy" / "config.json"
    return Path.home() / ".denim-daisy" / "config.json"


def _valid_value(key: str, value: Any) -> bool:
    if key in {"interval_minutes", "bubble_seconds"}:
        return isinstance(value, int) and not isinstance(value, bool) and value >= 1
    if key == "scale":
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and value > 0
        )
    if key == "pos":
        return (
            value is None
            or (
                isinstance(value, list)
                and len(value) == 2
                and all(
                    isinstance(item, int) and not isinstance(item, bool)
                    for item in value
                )
            )
        )
    if key in {"enabled", "walk_enabled", "schedule_enabled"}:
        return isinstance(value, bool)
    if key in {
        "ambient_walk_min_minutes",
        "ambient_walk_max_minutes",
        "walk_crossing_seconds",
    }:
        return isinstance(value, int) and not isinstance(value, bool) and value >= 1
    if key == "walk_drink_fraction":
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and 0.05 <= value <= 0.95
        )
    if key in {"schedule_start", "schedule_end"}:
        return schedule.is_valid_time_string(value)
    if key == "custom_reminders":
        return _valid_custom_reminders(value)
    return False


def load(path: Path | None = None) -> dict:
    target = path or config_path()
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("configuration must be an object")
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return copy.deepcopy(DEFAULTS)

    result = copy.deepcopy(DEFAULTS)
    for key in DEFAULTS:
        if key in raw and _valid_value(key, raw[key]):
            result[key] = raw[key]
    return result


def save(cfg: dict, path: Path | None = None) -> None:
    target = path or config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    result = copy.deepcopy(DEFAULTS)
    for key in DEFAULTS:
        if key in cfg and _valid_value(key, cfg[key]):
            result[key] = cfg[key]
    temporary = target.with_name(f"{target.name}.tmp")
    temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)
