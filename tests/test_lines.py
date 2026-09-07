import random

from daisy_pet.lines import TEMPLATES, ack_line, pick_line, tickle_line


def test_seeded_lines_are_deterministic():
    assert pick_line("cheerful", random.Random(4)) == pick_line(
        "cheerful", random.Random(4)
    )
    assert ack_line(random.Random(4)) == ack_line(random.Random(4))


def test_unknown_tone_uses_playful_pool():
    assert pick_line("unknown", random.Random(2)) in TEMPLATES["playful"]


def test_tickle_line_uses_expected_pool():
    assert tickle_line(random.Random(2)) in {
        "Hehe — that tickles!",
        "Eee! Stop it, that tickles!",
        "Hehehe, okay okay, I'm awake!",
    }
