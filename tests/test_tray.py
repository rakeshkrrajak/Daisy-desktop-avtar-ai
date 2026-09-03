from PySide6.QtGui import QPixmap

from daisy_pet.tray import DaisyTray


def _make_tray(qapp, **overrides):
    kwargs = dict(
        idle_frame=QPixmap(4, 4),
        drink_now=lambda: None,
        snooze=lambda: None,
        snooze_custom=lambda reminder_id: None,
        set_interval=lambda minutes: None,
        set_enabled=lambda enabled: None,
        quit_app=lambda: None,
        open_settings=lambda: None,
        interval=30,
        enabled=True,
    )
    kwargs.update(overrides)
    return DaisyTray(**kwargs)


def test_snooze_menu_starts_with_placeholder_when_no_custom_reminders(qapp):
    tray = _make_tray(qapp)
    actions = tray.snooze_custom_menu.actions()
    assert len(actions) == 1
    assert not actions[0].isEnabled()


def test_set_custom_reminders_populates_menu_and_triggers_callback(qapp):
    seen = []
    tray = _make_tray(qapp, snooze_custom=lambda reminder_id: seen.append(reminder_id))

    tray.set_custom_reminders(
        [("id1", "Stretch — every 30 min"), ("id2", "Lunch — daily at 13:00")]
    )
    actions = tray.snooze_custom_menu.actions()
    assert [a.text() for a in actions] == [
        "Stretch — every 30 min",
        "Lunch — daily at 13:00",
    ]

    tray.custom_snooze_actions["id2"].trigger()
    assert seen == ["id2"]


def test_set_custom_reminders_can_clear_back_to_placeholder(qapp):
    tray = _make_tray(qapp)
    tray.set_custom_reminders([("id1", "Stretch — every 30 min")])
    assert len(tray.snooze_custom_menu.actions()) == 1

    tray.set_custom_reminders([])
    actions = tray.snooze_custom_menu.actions()
    assert len(actions) == 1
    assert not actions[0].isEnabled()
