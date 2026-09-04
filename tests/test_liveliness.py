import random

import daisy_pet.liveliness as liveliness
from daisy_pet.sprites import CUSTOM_STATE_DIRS, STATES


def test_time_buckets_return_expected_behaviours():
    for hour in (0, 5, 22, 23, 6, 10, 11, 17, 18, 21):
        behaviour = liveliness.pick(hour, random.Random(4), None)
        assert behaviour in [item[0] for item in liveliness._bucket(hour)]


def test_pick_never_repeats_immediately_and_is_seeded():
    first = liveliness.pick(9, random.Random(8), None)
    second = liveliness.pick(9, random.Random(8), first.name)
    assert second.name != first.name
    assert liveliness.pick(9, random.Random(8), None) == first


def test_delay_bounds_and_clamping():
    rng = random.Random(4)
    assert 10 <= liveliness.next_delay_seconds(rng, 10, 20) <= 20
    assert liveliness.next_delay_seconds(rng, 20, 10) == 20


def test_behaviours_use_existing_states_and_chatter_is_boolean():
    valid = set(STATES) | set(CUSTOM_STATE_DIRS)
    all_behaviours = {
        item[0]
        for hour in range(24)
        for item in liveliness._bucket(hour)
    }
    assert all(
        behaviour.preferred in valid
        and behaviour.fallback in valid
        and isinstance(behaviour.chatter, bool)
        for behaviour in all_behaviours
    )
    assert all(len(liveliness._bucket(hour)) >= 2 for hour in range(24))
