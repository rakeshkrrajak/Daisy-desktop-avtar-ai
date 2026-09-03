import json

from daisy_pet.config import DEFAULTS, load, save


def test_config_roundtrip(tmp_path):
    path = tmp_path / "nested" / "config.json"
    expected = {**DEFAULTS, "interval_minutes": 45, "pos": [12, 34]}
    save(expected, path)
    assert load(path) == expected


def test_corrupt_file_falls_back_to_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{nope", encoding="utf-8")
    assert load(path) == DEFAULTS


def test_bad_types_and_unknown_keys_fall_back_or_drop(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "interval_minutes": "45",
                "bubble_seconds": 0,
                "scale": "large",
                "pos": [1, "two"],
                "enabled": "yes",
                "walk_enabled": "yes",
                "ambient_walk_min_minutes": 0,
                "ambient_walk_max_minutes": "8",
                "walk_crossing_seconds": -1,
                "walk_drink_fraction": 1.5,
                "schedule_enabled": "yes",
                "schedule_start": "25:99",
                "schedule_end": 100,
                "custom_reminders": "not-a-list",
                "extra": "discard me",
            }
        ),
        encoding="utf-8",
    )
    assert load(path) == DEFAULTS


def test_walk_and_schedule_roundtrip(tmp_path):
    path = tmp_path / "config.json"
    expected = {
        **DEFAULTS,
        "walk_enabled": False,
        "ambient_walk_min_minutes": 5,
        "ambient_walk_max_minutes": 15,
        "walk_crossing_seconds": 12,
        "walk_drink_fraction": 0.4,
        "schedule_enabled": True,
        "schedule_start": "09:30",
        "schedule_end": "17:45",
    }
    save(expected, path)
    assert load(path) == expected


def test_custom_reminders_roundtrip(tmp_path):
    path = tmp_path / "config.json"
    expected = {
        **DEFAULTS,
        "custom_reminders": [
            {"id": "a1", "text": "Stretch", "interval_minutes": 45, "enabled": True},
            {"id": "b2", "text": "Stand up", "interval_minutes": 20, "enabled": False},
        ],
    }
    save(expected, path)
    assert load(path) == expected


def test_custom_reminders_malformed_entries_fall_back_to_empty(tmp_path):
    path = tmp_path / "config.json"
    bad_entries = [
        [{"id": "", "text": "Stretch", "interval_minutes": 10, "enabled": True}],
        [{"id": "a1", "text": "   ", "interval_minutes": 10, "enabled": True}],
        [{"id": "a1", "text": "x" * 500, "interval_minutes": 10, "enabled": True}],
        [{"id": "a1", "text": "Stretch", "interval_minutes": 0, "enabled": True}],
        [{"id": "a1", "text": "Stretch", "interval_minutes": "10", "enabled": True}],
        [{"id": "a1", "text": "Stretch", "interval_minutes": 10, "enabled": "yes"}],
        [{"text": "Stretch", "interval_minutes": 10, "enabled": True}],
        ["not-a-dict"],
    ]
    for entries in bad_entries:
        path.write_text(
            json.dumps({"custom_reminders": entries}), encoding="utf-8"
        )
        assert load(path)["custom_reminders"] == []


def test_default_custom_reminders_list_is_not_shared_between_loads(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{}", encoding="utf-8")
    first = load(path)
    first["custom_reminders"].append({"id": "x"})
    second = load(path)
    assert second["custom_reminders"] == []


def test_custom_reminders_time_of_day_mode_roundtrip(tmp_path):
    path = tmp_path / "config.json"
    expected = {
        **DEFAULTS,
        "custom_reminders": [
            {
                "id": "a1",
                "text": "Afternoon check-in",
                "mode": "time_of_day",
                "interval_minutes": None,
                "time_of_day": "15:00",
                "snooze_minutes": 5,
                "enabled": True,
            },
        ],
    }
    save(expected, path)
    assert load(path) == expected


def test_custom_reminders_time_of_day_malformed_entries_fall_back_to_empty(tmp_path):
    path = tmp_path / "config.json"
    bad_entries = [
        [
            {
                "id": "a1",
                "text": "Lunch",
                "mode": "time_of_day",
                "time_of_day": "25:99",
                "enabled": True,
            }
        ],
        [
            {
                "id": "a1",
                "text": "Lunch",
                "mode": "time_of_day",
                "enabled": True,
            }
        ],
        [
            {
                "id": "a1",
                "text": "Lunch",
                "mode": "whenever",
                "interval_minutes": 10,
                "enabled": True,
            }
        ],
        [
            {
                "id": "a1",
                "text": "Lunch",
                "interval_minutes": 10,
                "enabled": True,
                "snooze_minutes": 0,
            }
        ],
    ]
    for entries in bad_entries:
        path.write_text(json.dumps({"custom_reminders": entries}), encoding="utf-8")
        assert load(path)["custom_reminders"] == []


def test_mood_and_ollama_defaults_and_validation(tmp_path):
    path = tmp_path / "config.json"
    assert load(path)["mood_enabled"] is True
    assert load(path)["ollama_enabled"] is False
    assert load(path)["ollama_url"] == "http://127.0.0.1:11434"
    assert load(path)["ollama_model"] == "llama3.2"
    path.write_text(
        json.dumps(
            {
                "mood_enabled": "yes",
                "ollama_enabled": "yes",
                "ollama_url": "https://127.0.0.1:11434",
                "ollama_model": "",
            }
        ),
        encoding="utf-8",
    )
    cfg = load(path)
    assert cfg["mood_enabled"] is True
    assert cfg["ollama_enabled"] is False
    assert cfg["ollama_url"] == DEFAULTS["ollama_url"]
    assert cfg["ollama_model"] == DEFAULTS["ollama_model"]


def test_non_local_ollama_url_is_rejected(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps({"ollama_url": "http://example.com:11434"}),
        encoding="utf-8",
    )
    assert load(path)["ollama_url"] == DEFAULTS["ollama_url"]


def test_custom_reminders_old_shape_without_mode_is_still_valid(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "custom_reminders": [
                    {
                        "id": "a1",
                        "text": "Stretch",
                        "interval_minutes": 20,
                        "enabled": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    assert load(path)["custom_reminders"] == [
        {"id": "a1", "text": "Stretch", "interval_minutes": 20, "enabled": True}
    ]
