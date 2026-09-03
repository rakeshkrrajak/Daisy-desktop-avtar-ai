import random

from daisy_pet.lines import TEMPLATES, ack_line, pick_line


def test_seeded_lines_are_deterministic():
    assert pick_line("cheerful", random.Random(4)) == pick_line(
        "cheerful", random.Random(4)
    )
    assert ack_line(random.Random(4)) == ack_line(random.Random(4))


def test_unknown_tone_uses_playful_pool():
    assert pick_line("unknown", random.Random(2)) in TEMPLATES["playful"]
