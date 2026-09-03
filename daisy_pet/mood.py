import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from .config import mood_state_path


MOODS = (
    "happy",
    "content",
    "neutral",
    "thinking",
    "waiting",
    "disappointed",
    "surprised",
    "sleepy",
)
POSE_FOR_MOOD: dict[str, tuple[str, str]] = {
    "happy": ("happy", "jumping"),
    "content": ("happy", "waving"),
    "neutral": ("idle", "idle"),
    "thinking": ("thinking", "review"),
    "waiting": ("judging", "waiting"),
    "disappointed": ("disappointed", "failed"),
    "surprised": ("surprised", "jumping"),
    "sleepy": ("sleepy", "waiting"),
}
TONE_FOR_MOOD: dict[str, str] = {
    "happy": "cheerful",
    "content": "cheerful",
    "neutral": "playful",
    "thinking": "gentle",
    "waiting": "firm",
    "disappointed": "firm",
    "surprised": "playful",
    "sleepy": "sleepy",
}


@dataclass(frozen=True)
class MoodSignals:
    hour: int
    minutes_since_ack: float | None
    snooze_streak: int
    ignored_streak: int
    just_acknowledged: bool = False
    just_snoozed: bool = False
    just_dragged: bool = False
    first_appearance_today: bool = False


@dataclass(frozen=True)
class MoodDecision:
    mood: str
    tone: str
    reason: str


def decide(signals: MoodSignals) -> MoodDecision:
    if not 0 <= signals.hour <= 23:
        raise ValueError("hour must be between 0 and 23")
    if signals.snooze_streak < 0 or signals.ignored_streak < 0:
        raise ValueError("streaks must not be negative")
    if signals.just_dragged:
        mood, reason = "surprised", "just_dragged"
    elif signals.just_acknowledged:
        mood, reason = "happy", "just_acknowledged"
    elif signals.just_snoozed and signals.snooze_streak >= 2:
        mood, reason = "disappointed", "snooze_streak>=2"
    elif signals.just_snoozed:
        mood, reason = "thinking", "just_snoozed"
    elif signals.ignored_streak >= 2:
        mood, reason = "waiting", "ignored_streak>=2"
    elif signals.hour >= 22 or signals.hour < 6:
        mood, reason = "sleepy", "night_hours"
    elif signals.first_appearance_today:
        mood, reason = "content", "first_appearance_today"
    elif signals.minutes_since_ack is None or signals.minutes_since_ack > 90:
        mood, reason = "waiting", "minutes_since_ack>90"
    else:
        mood, reason = "neutral", "default"
    return MoodDecision(mood, TONE_FOR_MOOD[mood], reason)


@dataclass
class MoodState:
    last_ack_iso: str | None = None
    snooze_streak: int = 0
    ignored_streak: int = 0
    last_seen_date: str | None = None

    def record_ack(self, now: datetime) -> None:
        self.last_ack_iso = now.isoformat()
        self.snooze_streak = 0
        self.ignored_streak = 0

    def record_snooze(self) -> None:
        self.snooze_streak += 1

    def record_ignored(self) -> None:
        self.ignored_streak += 1

    def mark_seen(self, today: date | str) -> bool:
        value = today.isoformat() if isinstance(today, date) else today
        first = self.last_seen_date != value
        self.last_seen_date = value
        return first


def load(path: Path | None = None) -> MoodState:
    target = path or mood_state_path()
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("mood state must be an object")
        state = MoodState(
            last_ack_iso=raw.get("last_ack_iso"),
            snooze_streak=raw.get("snooze_streak", 0),
            ignored_streak=raw.get("ignored_streak", 0),
            last_seen_date=raw.get("last_seen_date"),
        )
        if state.last_ack_iso is not None and not isinstance(state.last_ack_iso, str):
            raise ValueError("bad last_ack_iso")
        if (
            not isinstance(state.snooze_streak, int)
            or isinstance(state.snooze_streak, bool)
            or state.snooze_streak < 0
        ):
            raise ValueError("bad snooze_streak")
        if (
            not isinstance(state.ignored_streak, int)
            or isinstance(state.ignored_streak, bool)
            or state.ignored_streak < 0
        ):
            raise ValueError("bad ignored_streak")
        if state.last_seen_date is not None and not isinstance(state.last_seen_date, str):
            raise ValueError("bad last_seen_date")
        return state
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return MoodState()


def save(state: MoodState, path: Path | None = None) -> None:
    target = path or mood_state_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "last_ack_iso": state.last_ack_iso,
        "snooze_streak": state.snooze_streak,
        "ignored_streak": state.ignored_streak,
        "last_seen_date": state.last_seen_date,
    }
    temporary = target.with_name(f"{target.name}.tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)
