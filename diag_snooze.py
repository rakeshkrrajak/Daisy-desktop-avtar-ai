from PySide6.QtWidgets import QApplication

from daisy_pet import config
from daisy_pet.app import DaisyApplication

cfg = config.load()
cfg["custom_reminders"] = [
    {
        "id": "t1",
        "text": "Stretch",
        "mode": "interval",
        "interval_minutes": 30,
        "time_of_day": None,
        "snooze_minutes": 7,
        "enabled": True,
    },
    {
        "id": "t2",
        "text": "Lunch",
        "mode": "time_of_day",
        "interval_minutes": None,
        "time_of_day": "13:00",
        "snooze_minutes": 15,
        "enabled": True,
    },
]
config.save(cfg)

app = QApplication([])
app.setQuitOnLastWindowClosed(False)
controller = DaisyApplication(app)

print("tray snooze actions:", list(controller.tray.custom_snooze_actions.keys()))
print(
    "tray labels:",
    [a.text() for a in controller.tray.snooze_custom_menu.actions()],
)

before = controller.custom_reminders.find("t1").seconds_remaining
controller.snooze_custom("t1")
after = controller.custom_reminders.find("t1").seconds_remaining
print("t1 seconds_remaining before:", round(before, 1), "after snooze:", round(after, 1))
assert after > before
assert round(after) == 7 * 60

controller.snooze_custom("nonexistent")  # should be a no-op, not raise
print("no-op snooze on unknown id: OK")

print("ALL CHECKS PASSED")
