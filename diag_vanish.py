import time

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from daisy_pet import config
from daisy_pet.app import DaisyApplication

cfg = config.load()
cfg["interval_minutes"] = 1
cfg["bubble_seconds"] = 5
cfg["custom_reminders"] = []
config.save(cfg)

app = QApplication([])
app.setQuitOnLastWindowClosed(False)
controller = DaisyApplication(app)

log = []


def snapshot():
    log.append(
        (
            round(time.monotonic(), 1),
            controller.pet.x(),
            controller.pet.state,
            controller.walker.busy,
            controller.pet.isVisible(),
            controller.pet.is_walking,
        )
    )


watch_timer = QTimer()
watch_timer.setInterval(300)
watch_timer.timeout.connect(snapshot)
watch_timer.start()


# Wait until she's mid-reminder (drinking pose), then simulate a double-click
# to vanish her mid-cinematic, and verify the stale _finish_reminder_walk
# singleShot doesn't revive her afterward.
def maybe_vanish():
    if controller.pet.state == "drinking" and not vanished["done"]:
        vanished["done"] = True
        print("VANISHING NOW at", round(time.monotonic(), 1), flush=True)
        controller._vanish_now()


vanished = {"done": False}
poke_timer = QTimer()
poke_timer.setInterval(200)
poke_timer.timeout.connect(maybe_vanish)
poke_timer.start()

QTimer.singleShot(90_000, app.quit)
app.exec()

for row in log:
    print(row, flush=True)
