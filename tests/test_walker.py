import random
import time
from pathlib import Path

import pytest
from PySide6.QtCore import QPoint

from daisy_pet.pet_window import PetWindow
from daisy_pet.sprites import SpriteSheet
from daisy_pet.walker import Walker


@pytest.fixture
def sheet(qapp):
    return SpriteSheet(
        Path(__file__).parents[1] / "daisy_pet" / "assets" / "spritesheet.webp"
    )


def _wait_until(predicate, timeout=3):
    from PySide6.QtWidgets import QApplication

    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        QApplication.instance().processEvents()
        time.sleep(0.01)
    return predicate()


def test_ambient_walk_moves_pet_and_clears_busy(qapp, sheet):
    pet = PetWindow(sheet)
    pet.move(500, 10)
    walker = Walker(pet, rng=random.Random(1))

    started = walker.ambient_walk(0.2)
    assert started
    assert walker.busy

    assert _wait_until(lambda: not walker.busy)
    assert pet.state == "idle"
    assert pet.y() == walker.baseline_y()


def test_ambient_walk_is_noop_while_busy(qapp, sheet):
    pet = PetWindow(sheet)
    pet.move(10, 10)
    walker = Walker(pet, rng=random.Random(1))
    walker.busy = True
    assert walker.ambient_walk(1) is False


def test_ambient_walk_targets_a_position_to_the_left(qapp, sheet, monkeypatch):
    pet = PetWindow(sheet)
    pet.move(500, 10)
    walker = Walker(pet, rng=random.Random(1))
    targets = []
    monkeypatch.setattr(
        pet,
        "start_walk",
        lambda target, speed, callback: targets.append(target),
    )

    assert walker.ambient_walk(1)
    assert targets[0] <= 500 - pet.width()


def test_ambient_walk_from_left_edge_restarts_at_right_corner(
    qapp, sheet, monkeypatch
):
    pet = PetWindow(sheet)
    area = qapp.primaryScreen().availableGeometry()
    pet.move(area.left(), 10)
    walker = Walker(pet, rng=random.Random(1))
    targets = []
    monkeypatch.setattr(
        pet,
        "start_walk",
        lambda target, speed, callback: targets.append(target),
    )

    assert walker.ambient_walk(1)
    right_corner_x = area.right() + 1 - pet.width()
    assert pet.x() == right_corner_x
    assert targets[0] <= right_corner_x - pet.width()


def test_reminder_walk_in_stops_at_drink_fraction_then_out(qapp, sheet):
    pet = PetWindow(sheet)
    pet.move(10, 10)
    pet.hide()
    walker = Walker(pet, rng=random.Random(2))

    arrived = []

    def on_drink_point():
        arrived.append(True)

    walker.reminder_walk_in(0.2, 0.4, on_drink_point)
    area = walker.screen_area()
    entry_x = area.right() + 24
    far_x = area.left() + 24
    expected_drink_x = round(entry_x - 0.4 * (entry_x - far_x))
    assert pet.isVisible()
    assert walker.busy
    assert pet.pos() == QPoint(entry_x, walker.baseline_y(area))

    assert _wait_until(lambda: arrived)
    assert pet.x() == expected_drink_x

    exited = []
    walker.reminder_walk_out(0.2, lambda: exited.append(True))
    assert _wait_until(lambda: exited)
    assert not walker.busy
    assert pet.x() == area.left() - 24
    assert pet.state == "running-left"
