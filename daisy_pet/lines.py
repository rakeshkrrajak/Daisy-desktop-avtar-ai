import random

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


def pick_observation(
    kind: str, rng: random.Random | None = None
) -> str:
    chooser = rng or random
    return chooser.choice(OBSERVATION_LINES[kind])
