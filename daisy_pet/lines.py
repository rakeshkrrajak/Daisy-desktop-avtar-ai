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
