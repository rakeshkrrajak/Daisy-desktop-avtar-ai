import time
from pathlib import Path

import pytest

from daisy_pet.pet_window import PetWindow
from daisy_pet.pet_window import FRAME_MS
from daisy_pet.sprites import SpriteSheet


@pytest.fixture
def sheet(qapp):
    return SpriteSheet(
        Path(__file__).parents[1] / "daisy_pet" / "assets" / "spritesheet.webp"
    )


def test_play_with_loops_none_repeats_forever(qapp, sheet):
    pet = PetWindow(sheet)
    pet.play("running-left", loops=None)
    for _ in range(3 * len(pet._frames)):
        pet._advance()
    assert pet.state == "running-left"


def test_single_frame_custom_state_returns_to_then(qapp, sheet):
    pet = PetWindow(sheet)
    pet.play("happy", loops=2, then="idle")
    assert pet.state == "happy"
    assert pet._single_frame_timer.isActive()
    pet._finish_single_frame()
    assert pet.state == "idle"


def test_drinking_uses_slow_frame_interval(qapp, sheet):
    pet = PetWindow(sheet)
    pet.play("drinking", loops=None)
    assert pet._timer.interval() == FRAME_MS["drinking"]


def test_start_walk_picks_direction_from_target(qapp, sheet):
    pet = PetWindow(sheet)
    pet.move(500, 100)
    pet.start_walk(100, pixels_per_sec=1000)
    assert pet.state == "running-left"

    pet2 = PetWindow(sheet)
    pet2.move(100, 100)
    pet2.start_walk(500, pixels_per_sec=1000)
    assert pet2.state == "running-right"


def test_walk_reaches_target_and_calls_callback(qapp, sheet):
    pet = PetWindow(sheet)
    pet.move(500, 100)
    finished = []
    pet.start_walk(
        100, pixels_per_sec=2000, on_finished=lambda: finished.append(True), tick_ms=10
    )
    assert pet.is_walking

    deadline = time.monotonic() + 3
    while not finished and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.01)

    assert finished == [True]
    assert pet.x() == 100
    assert not pet.is_walking


def test_walk_defaults_to_idle_without_callback(qapp, sheet):
    pet = PetWindow(sheet)
    pet.move(120, 100)
    pet.start_walk(100, pixels_per_sec=2000, tick_ms=10)

    deadline = time.monotonic() + 3
    while pet.is_walking and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.01)

    assert pet.x() == 100
    assert pet.state == "idle"


def test_start_sip_uses_custom_drinking_art_when_available(qapp, sheet):
    pet = PetWindow(sheet)
    pet.start_sip(duration_ms=100)
    assert pet.state == "drinking"
    assert pet._sip_active
    assert pet._sip_uses_custom_art
    # Custom art is a real drawn pose, so no procedural glass tilt timer runs.
    assert not pet._sip_timer.isActive()

    deadline = time.monotonic() + 2
    while pet._sip_active and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.01)

    assert not pet._sip_active


def test_start_sip_falls_back_to_review_pose_and_glass(qapp, sheet, monkeypatch):
    pet = PetWindow(sheet)
    monkeypatch.setattr(sheet, "has_custom_state", lambda state: False)
    pet.start_sip(duration_ms=100)
    assert pet.state == "review"
    assert pet._sip_active
    assert not pet._sip_uses_custom_art
    assert pet._sip_timer.isActive()

    deadline = time.monotonic() + 2
    while pet._sip_active and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.01)

    assert not pet._sip_active
    assert not pet._sip_timer.isActive()


def test_sip_tilt_animates_and_resets_on_stop(qapp, sheet, monkeypatch):
    monkeypatch.setattr(sheet, "has_custom_state", lambda state: False)
    pet = PetWindow(sheet)
    pet.start_sip(duration_ms=10_000)
    for _ in range(5):
        pet._animate_sip()
    assert pet._sip_tilt > 0

    pet.stop_sip()
    assert pet._sip_tilt == 0
    assert not pet._sip_active
    assert not pet._sip_timer.isActive()


def test_double_click_emits_double_clicked_signal(qapp, sheet):
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QMouseEvent

    pet = PetWindow(sheet)
    pet.move(100, 100)
    seen = []
    pet.double_clicked.connect(lambda: seen.append(True))

    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonDblClick,
        QPointF(5, 5),
        QPointF(5, 5),
        QPointF(5, 5),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    pet.mouseDoubleClickEvent(event)
    assert seen == [True]


def test_double_click_ignores_right_button(qapp, sheet):
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QMouseEvent

    pet = PetWindow(sheet)
    pet.move(100, 100)
    seen = []
    pet.double_clicked.connect(lambda: seen.append(True))

    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonDblClick,
        QPointF(5, 5),
        QPointF(5, 5),
        QPointF(5, 5),
        Qt.MouseButton.RightButton,
        Qt.MouseButton.RightButton,
        Qt.KeyboardModifier.NoModifier,
    )
    pet.mouseDoubleClickEvent(event)
    assert seen == []


def test_double_click_works_while_walking(qapp, sheet):
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QMouseEvent

    pet = PetWindow(sheet)
    pet.move(500, 100)
    pet.start_walk(100, pixels_per_sec=10)
    assert pet.is_walking
    seen = []
    pet.double_clicked.connect(lambda: seen.append(True))

    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonDblClick,
        QPointF(5, 5),
        QPointF(5, 5),
        QPointF(5, 5),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    pet.mouseDoubleClickEvent(event)
    assert seen == [True]  # double-click dismissal isn't blocked by the walk guard
    pet.stop_walk()


def test_right_click_emits_right_clicked_signal(qapp, sheet):
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QMouseEvent

    pet = PetWindow(sheet)
    pet.move(100, 100)
    seen = []
    pet.right_clicked.connect(lambda: seen.append(True))

    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(5, 5),
        QPointF(5, 5),
        QPointF(5, 5),
        Qt.MouseButton.RightButton,
        Qt.MouseButton.RightButton,
        Qt.KeyboardModifier.NoModifier,
    )
    pet.mousePressEvent(event)
    assert seen == [True]


def test_right_click_ignored_while_walking(qapp, sheet):
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QMouseEvent

    pet = PetWindow(sheet)
    pet.move(500, 100)
    pet.start_walk(100, pixels_per_sec=10)
    seen = []
    pet.right_clicked.connect(lambda: seen.append(True))

    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(5, 5),
        QPointF(5, 5),
        QPointF(5, 5),
        Qt.MouseButton.RightButton,
        Qt.MouseButton.RightButton,
        Qt.KeyboardModifier.NoModifier,
    )
    pet.mousePressEvent(event)
    assert seen == []
    pet.stop_walk()


def test_dragging_is_ignored_while_walking(qapp, sheet):
    pet = PetWindow(sheet)
    pet.move(500, 100)
    pet.start_walk(100, pixels_per_sec=10)
    assert pet.is_walking
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QMouseEvent

    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(5, 5),
        QPointF(5, 5),
        QPointF(5, 5),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    pet.mousePressEvent(event)
    assert pet._press_global is None

    pet.stop_walk()
