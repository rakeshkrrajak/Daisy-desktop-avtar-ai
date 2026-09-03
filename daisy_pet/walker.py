"""Coordinates Daisy's on-screen wandering and reminder walk-ins."""

from __future__ import annotations

import random
from collections.abc import Callable

from PySide6.QtCore import QRect
from PySide6.QtGui import QGuiApplication

from .pet_window import PetWindow

ENTRY_MARGIN = 24


class Walker:
    def __init__(self, pet: PetWindow, rng: random.Random | None = None) -> None:
        self.pet = pet
        self.rng = rng or random.Random()
        self.busy = False

    def screen_area(self) -> QRect:
        screen = (
            QGuiApplication.screenAt(self.pet.geometry().center())
            or self.pet.screen()
            or QGuiApplication.primaryScreen()
        )
        if screen is None:
            return QRect(0, 0, 1024, 768)
        return screen.availableGeometry()

    def baseline_y(self, area: QRect | None = None) -> int:
        area = area or self.screen_area()
        return area.bottom() - self.pet.height()

    def speed_for(self, crossing_seconds: float, area: QRect | None = None) -> float:
        area = area or self.screen_area()
        distance = max(1, area.width())
        return distance / max(0.5, crossing_seconds)

    def ambient_walk(
        self, crossing_seconds: float, on_done: Callable[[], None] | None = None
    ) -> bool:
        """Wander to a random spot along the baseline. No-op while busy."""
        if self.busy:
            return False
        area = self.screen_area()
        min_x = area.left()
        max_x = area.right() - self.pet.width()
        if max_x <= min_x:
            return False
        target_x = self.rng.randint(min_x, max_x)
        if abs(target_x - self.pet.x()) < self.pet.width():
            return False

        self.busy = True
        self.pet.move(self.pet.x(), self.baseline_y(area))

        def finished() -> None:
            self.busy = False
            self.pet.play("idle")
            if on_done is not None:
                on_done()

        self.pet.start_walk(target_x, self.speed_for(crossing_seconds, area), finished)
        return True

    def reminder_walk_in(
        self,
        crossing_seconds: float,
        drink_fraction: float,
        on_drink_point: Callable[[], None],
    ) -> None:
        """Bring Daisy in from the right edge and walk her partway across.

        She stops at `drink_fraction` of the full right-to-left crossing
        distance (e.g. 0.4 means 40% of the way in) and `on_drink_point` is
        called there so she can act out the reminder.
        """
        area = self.screen_area()
        entry_x = area.right() + ENTRY_MARGIN
        far_x = area.left() + ENTRY_MARGIN
        drink_x = round(entry_x - drink_fraction * (entry_x - far_x))
        self.busy = True
        self.pet.move(entry_x, self.baseline_y(area))
        self.pet.show()
        self.pet.start_walk(
            drink_x, self.speed_for(crossing_seconds, area), on_drink_point
        )

    def reminder_walk_out(
        self, crossing_seconds: float, on_exited: Callable[[], None]
    ) -> None:
        """Continue walking left off-screen after the drink pause, then vanish."""
        area = self.screen_area()
        exit_x = area.left() - ENTRY_MARGIN

        def finished() -> None:
            self.busy = False
            on_exited()

        self.pet.start_walk(exit_x, self.speed_for(crossing_seconds, area), finished)
