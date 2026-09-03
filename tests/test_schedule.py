from datetime import datetime

import pytest

from daisy_pet.schedule import is_active, is_valid_time_string, parse_time


def test_is_valid_time_string():
    assert is_valid_time_string("08:00")
    assert is_valid_time_string("23:59")
    assert not is_valid_time_string("24:00")
    assert is_valid_time_string("8:00")
    assert not is_valid_time_string("08:60")
    assert not is_valid_time_string("not-a-time")
    assert not is_valid_time_string(None)


def test_parse_time_rejects_invalid_strings():
    with pytest.raises(ValueError):
        parse_time("nope")


def test_same_day_window():
    start, end = "08:00", "18:00"
    assert is_active(start, end, datetime(2024, 1, 1, 8, 0))
    assert is_active(start, end, datetime(2024, 1, 1, 12, 30))
    assert not is_active(start, end, datetime(2024, 1, 1, 18, 0))
    assert not is_active(start, end, datetime(2024, 1, 1, 7, 59))
    assert not is_active(start, end, datetime(2024, 1, 1, 23, 0))


def test_overnight_window():
    start, end = "22:00", "06:00"
    assert is_active(start, end, datetime(2024, 1, 1, 23, 0))
    assert is_active(start, end, datetime(2024, 1, 1, 3, 0))
    assert not is_active(start, end, datetime(2024, 1, 1, 12, 0))
    assert not is_active(start, end, datetime(2024, 1, 1, 6, 0))


def test_equal_start_and_end_is_always_active():
    assert is_active("09:00", "09:00", datetime(2024, 1, 1, 3, 0))
    assert is_active("09:00", "09:00", datetime(2024, 1, 1, 23, 0))
