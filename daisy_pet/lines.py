import random
import re

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
