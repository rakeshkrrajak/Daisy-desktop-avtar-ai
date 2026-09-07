import random
import re

from .memory import DaySummary
from .reminder import MESSAGES


TEMPLATES: dict[str, tuple[str, ...]] = {
    "cheerful": (
        "Hydration station! Your body called.",
        "Tiny sip, big productivity.",
        "Drink some water, superstar.",
        "Daisy says: refresh and sparkle!",
    ),
    "gentle": (
        "A gentle sip can make the whole day kinder.",
        "Take a small, refreshing water break.",
        "No rush — just a cozy sip of water.",
        "Your future self would love a glass of water.",
    ),
    "firm": (
        "Sip happens. Please drink your water.",
        "Daisy is waiting for that glass.",
        "Hydration is not optional, friend.",
        "Water first, then back to winning.",
    ),
    "sleepy": (
        "Sleepy Daisy says: one quiet sip, please.",
        "A little water before dreamland?",
        "Hydrate gently, then get some rest.",
        "Night sip unlocked.",
    ),
    "playful": MESSAGES,
}

OBSERVATION_LINES: dict[str, tuple[str, ...]] = {
    "meeting": (
        "Meeting mode? Keep a sip nearby, superstar.",
        "Daisy sees meeting mode — remember your water.",
    ),
    "message": (
        "A message popped up. Take a refreshing sip too?",
        "New message, new sip — multitasking!",
    ),
    "browser_sprawl": (
        "That's a lot of browser windows. Want to close a few?",
        "So many tabs… and one glass of water, please.",
    ),
    "long_focus": (
        "You've been focused a while — stretch and sip?",
        "Brilliant focus. Give your body a water break.",
    ),
    "idle_return": (
        "Welcome back! A refreshing sip before you dive in?",
        "Back again? Let's make it a hydrated return.",
    ),
    "sitting": (
        "You've been sitting 90 minutes — stretch and sip?",
        "Daisy says: stand up, stretch, and take a sip.",
    ),
}
STALE_TAB_PREFIXES = (
    "Untouched for {age}: {titles}. Close a few?",
    "These tabs have been waiting {age}: {titles}. Close a few?",
)
TAB_REVIEW_DONE_LINES = (
    "All clear — Daisy will leave those tabs alone for now.",
    "Review complete. Your browser gets a little breathing room.",
)
APP_LABELS = {
    "code.exe": "VS Code",
    "devenv.exe": "Visual Studio",
    "teams.exe": "Teams",
    "ms-teams.exe": "Teams",
    "outlook.exe": "Outlook",
    "chrome.exe": "Chrome",
    "msedge.exe": "Edge",
    "firefox.exe": "Firefox",
    "explorer.exe": "File Explorer",
    "winword.exe": "Word",
    "excel.exe": "Excel",
    "powerpnt.exe": "PowerPoint",
    "windowsterminal.exe": "Terminal",
    "powershell.exe": "PowerShell",
    "slack.exe": "Slack",
}
EMPTY_SUMMARY_LINES = (
    "Nothing on today's page yet — Daisy just kept you company.",
    "Today is still a blank page. Daisy was watching quietly.",
)
SUMMARY_APP_LIMIT = 3
SUMMARY_DUE_LIMIT = 2
IDLE_CHATTER = (
    "Just keeping you company.",
    "A tiny Daisy check-in.",
    "Hope your day is blooming.",
    "Quietly cheering you on.",
)


def pick_line(tone: str, rng: random.Random | None = None) -> str:
    chooser = rng or random
    return chooser.choice(TEMPLATES.get(tone, TEMPLATES["playful"]))


def ack_line(rng: random.Random | None = None) -> str:
    chooser = rng or random
    return chooser.choice(
        (
            "Nice sip! Daisy is proud of you.",
            "That was refreshing — well done!",
            "Hydration high five!",
            "Excellent choice. Keep glowing!",
        )
    )


def water_ack_line(rng: random.Random | None = None) -> str:
    chooser = rng or random
    return chooser.choice(
        (
            "Thanks for drinking it!",
            "Nice work — thank you for hydrating!",
            "Yay, thank you for the sip!",
        )
    )


def snooze_line(minutes: int, rng: random.Random | None = None) -> str:
    chooser = rng or random
    return chooser.choice(
        (
            f"Snoozed for {minutes} minutes. Daisy will remind you!",
            f"Okay — I'll wait {minutes} minutes before asking again.",
        )
    )


def tickle_line(rng: random.Random | None = None) -> str:
    chooser = rng or random
    return chooser.choice(
        (
            "Hehe — that tickles!",
            "Eee! Stop it, that tickles!",
            "Hehehe, okay okay, I'm awake!",
        )
    )


def pick_observation(
    kind: str, rng: random.Random | None = None
) -> str:
    chooser = rng or random
    return chooser.choice(OBSERVATION_LINES[kind])


def stale_tab_line(
    titles: list[str] | tuple[str, ...],
    minutes: int,
    rng: random.Random | None = None,
) -> str:
    chooser = rng or random
    cleaned = []
    for title in titles[:2]:
        title = re.sub(r"\s+", " ", title).strip()
        if len(title) > 40:
            title = f"{title[:39]}…"
        cleaned.append(f'"{title}"')
    prefix = chooser.choice(STALE_TAB_PREFIXES)
    minutes = max(1, int(minutes))
    age = f"{minutes} min" if minutes < 60 else f"{minutes // 60}h+"
    line = prefix.format(age=age, titles=", ".join(cleaned))
    return line if len(line) <= 220 else f"{line[:219]}…"


def tab_review_line(title: str) -> str:
    cleaned = re.sub(r"\s+", " ", title).strip()
    if len(cleaned) > 40:
        cleaned = f"{cleaned[:39]}…"
    return f'Close "{cleaned}"? Press Ctrl+W — or Keep it and I\'ll ask tomorrow.'


def tab_review_done_line(rng: random.Random | None = None) -> str:
    chooser = rng or random
    return chooser.choice(TAB_REVIEW_DONE_LINES)


def idle_chatter(rng: random.Random | None = None) -> str:
    chooser = rng or random
    return chooser.choice(IDLE_CHATTER)


def app_label(process: str) -> str:
    key = process.strip().lower()
    if key in APP_LABELS:
        return APP_LABELS[key]
    stem = key.removesuffix(".exe")
    return stem.replace("_", " ").replace("-", " ").title() or "something"


def _time_spent(seconds: int) -> str:
    minutes = max(0, int(seconds)) // 60
    if minutes < 60:
        return f"{minutes} min"
    hours, rest = divmod(minutes, 60)
    return f"{hours}h" if rest < 6 else f"{hours}h{rest:02d}"


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def _short_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    return f"{cleaned[:39]}…" if len(cleaned) > 40 else cleaned


def day_summary_line(
    summary: DaySummary, rng: random.Random | None = None
) -> str:
    chooser = rng or random
    if summary.empty:
        return chooser.choice(EMPTY_SUMMARY_LINES)
    parts = [
        f"{_time_spent(seconds)} in {app_label(process)}"
        for process, seconds in summary.app_seconds[:SUMMARY_APP_LIMIT]
        if seconds >= 60
    ]
    if summary.sips_offered:
        parts.append(f"{summary.sips_acknowledged} of {summary.sips_offered} sips")
    if summary.tabs_kept:
        parts.append(f"{_plural(summary.tabs_kept, 'tab')} kept")
    if summary.tabs_closed:
        parts.append(f"{_plural(summary.tabs_closed, 'tab')} closed")
    if summary.notes:
        parts.append(_plural(len(summary.notes), "note"))
    line = f"Today: {' · '.join(parts)}" if parts else "Today: a quiet one so far"
    if summary.notes_due:
        due = "; ".join(
            _short_text(note.text) for note in summary.notes_due[:SUMMARY_DUE_LIMIT]
        )
        line = f"{line} — due today: {due}"
    return line if len(line) <= 220 else f"{line[:219]}…"
