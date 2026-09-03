from collections.abc import Callable

from PySide6.QtCore import QPoint, QRect, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QGuiApplication, QMouseEvent, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from .sprites import SpriteSheet

# Where the glass is drawn, as fractions of the current frame size, so it
# scales along with Daisy and roughly lines up with her clasped hands in
# the "review" pose.
GLASS_ANCHOR_X_FRAC = 0.5
GLASS_ANCHOR_Y_FRAC = 0.38
GLASS_WIDTH_FRAC = 0.16
GLASS_HEIGHT_FRAC = 0.2
SIP_TILT_MAX_DEGREES = 22
SIP_TILT_STEP_DEGREES = 4


class PetWindow(QWidget):
    moved = Signal(QPoint)
    clicked = Signal()
    right_clicked = Signal()
    double_clicked = Signal()

    def __init__(
        self,
        sprites: SpriteSheet,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.sprites = sprites
        self._state = "idle"
        self._frames = sprites.frames("idle")
        self._frame_index = 0
        self._remaining_loops: int | None = None
        self._then = "idle"
        self._press_global: QPoint | None = None
        self._press_offset: QPoint | None = None
        self._dragged = False
        width, height = sprites.frame_size
        self.setFixedSize(width, height)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._advance)
        self._timer.start()
        self._walk_timer = QTimer(self)
        self._walk_timer.timeout.connect(self._walk_tick)
        self._walk_target_x = 0
        self._walk_step = 0.0
        self._walk_remainder = 0.0
        self._walk_on_finished: Callable[[], None] | None = None
        self._sip_timer = QTimer(self)
        self._sip_timer.timeout.connect(self._animate_sip)
        self._sip_tilt = 0.0
        self._sip_direction = 1
        self._sip_uses_custom_art = False
        self._sip_active = False

    @property
    def current_frame(self) -> QPixmap:
        return self._frames[self._frame_index]

    @property
    def state(self) -> str:
        return self._state

    @property
    def is_walking(self) -> bool:
        return self._walk_timer.isActive()

    def play(self, state: str, loops: int | None = 1, then: str = "idle") -> None:
        frames = self.sprites.frames(state)
        self.sprites.frames(then)
        if loops is not None and loops < 1:
            raise ValueError("loops must be at least 1")
        self._state = state
        self._frames = frames
        self._frame_index = 0
        self._remaining_loops = None if state == "idle" else loops
        self._then = then
        self.update()

    def _switch_to(self, state: str) -> None:
        self._state = state
        self._frames = self.sprites.frames(state)
        self._frame_index = 0

    def _advance(self) -> None:
        if len(self._frames) == 1:
            return
        self._frame_index += 1
        if self._frame_index < len(self._frames):
            self.update()
            return
        self._frame_index = 0
        if self._remaining_loops is not None:
            self._remaining_loops -= 1
            if self._remaining_loops <= 0:
                self._remaining_loops = None
                self._switch_to(self._then)
        self.update()

    def place_initial(self, position: list[int] | None) -> None:
        candidate = QPoint(*position) if position is not None else None
        screens = QGuiApplication.screens()
        if candidate is not None and any(
            screen.availableGeometry().intersects(
                QRect(candidate, self.size())
            )
            for screen in screens
        ):
            self.move(candidate)
            return
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            self.move(40, 40)
            return
        area = screen.availableGeometry()
        self.move(
            area.right() - self.width() - 40,
            area.bottom() - self.height() - 40,
        )

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.drawPixmap(0, 0, self.current_frame)
        if self._sip_active and not self._sip_uses_custom_art:
            painter.setRenderHint(QPainter.Antialiasing)
            self._paint_glass(painter)

    def start_sip(self, duration_ms: int = 1800) -> None:
        """Act out drinking: a dedicated sprite if one's provided, otherwise
        the hands-near-chin pose with a drawn glass tilting toward her mouth.
        """
        self._sip_active = True
        self._sip_uses_custom_art = self.sprites.has_custom_state("drinking")
        if self._sip_uses_custom_art:
            self.play("drinking", loops=None)
        else:
            self.play("review", loops=None)
            self._sip_tilt = 0.0
            self._sip_direction = 1
            self._sip_timer.start(40)
        QTimer.singleShot(duration_ms, self.stop_sip)

    def stop_sip(self) -> None:
        self._sip_active = False
        self._sip_timer.stop()
        self._sip_tilt = 0.0
        self.update()

    def _animate_sip(self) -> None:
        self._sip_tilt += SIP_TILT_STEP_DEGREES * self._sip_direction
        if self._sip_tilt >= SIP_TILT_MAX_DEGREES:
            self._sip_tilt = SIP_TILT_MAX_DEGREES
            self._sip_direction = -1
        elif self._sip_tilt <= 0:
            self._sip_tilt = 0
            self._sip_direction = 1
        self.update()

    def _paint_glass(self, painter: QPainter) -> None:
        width = self.width() * GLASS_WIDTH_FRAC
        height = self.height() * GLASS_HEIGHT_FRAC
        anchor_x = self.width() * GLASS_ANCHOR_X_FRAC
        anchor_y = self.height() * GLASS_ANCHOR_Y_FRAC
        painter.save()
        painter.translate(anchor_x, anchor_y)
        painter.rotate(-self._sip_tilt)
        glass = QRectF(-width / 2, -height * 0.85, width, height)
        painter.setPen(QPen(QColor("#5b7c99"), max(1.0, width * 0.08)))
        painter.setBrush(QColor(255, 255, 255, 225))
        painter.drawRoundedRect(glass, width * 0.15, width * 0.15)
        water = QRectF(
            glass.left() + width * 0.12,
            glass.top() + height * 0.4,
            glass.width() - width * 0.24,
            glass.height() * 0.5,
        )
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#4fa8e0"))
        painter.drawRoundedRect(water, width * 0.1, width * 0.1)
        painter.restore()

    def start_walk(
        self,
        target_x: int,
        pixels_per_sec: float,
        on_finished: Callable[[], None] | None = None,
        tick_ms: int = 30,
    ) -> None:
        """Walk horizontally to `target_x`, animating the matching direction."""
        if pixels_per_sec <= 0:
            raise ValueError("pixels_per_sec must be positive")
        direction = "running-right" if target_x > self.x() else "running-left"
        self.play(direction, loops=None)
        self._walk_target_x = target_x
        step = pixels_per_sec * tick_ms / 1000.0
        self._walk_step = step if target_x > self.x() else -step
        self._walk_remainder = 0.0
        self._walk_on_finished = on_finished
        self._walk_timer.start(tick_ms)

    def stop_walk(self) -> None:
        self._walk_timer.stop()
        self._walk_on_finished = None

    def _walk_tick(self) -> None:
        self._walk_remainder += self._walk_step
        step = int(self._walk_remainder)
        self._walk_remainder -= step
        new_x = self.x() + step
        reached = (
            (self._walk_step >= 0 and new_x >= self._walk_target_x)
            or (self._walk_step < 0 and new_x <= self._walk_target_x)
        )
        if reached:
            new_x = self._walk_target_x
        self.move(new_x, self.y())
        if not reached:
            return
        self._walk_timer.stop()
        callback = self._walk_on_finished
        self._walk_on_finished = None
        if callback is not None:
            callback()
        else:
            self.play("idle")

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self.is_walking:
            return
        if event.button() == Qt.LeftButton:
            self._press_global = event.globalPosition().toPoint()
            self._press_offset = self._press_global - self.pos()
            self._dragged = False
        elif event.button() == Qt.RightButton:
            self.right_clicked.emit()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if (
            self._press_global is not None
            and self._press_offset is not None
            and event.buttons() & Qt.LeftButton
        ):
            current = event.globalPosition().toPoint()
            if (current - self._press_global).manhattanLength() >= 4:
                self._dragged = True
                self.move(current - self._press_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton and self._press_global is not None:
            if self._dragged:
                self.moved.emit(self.pos())
            else:
                self.clicked.emit()
        self._press_global = None
        self._press_offset = None
        self._dragged = False
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)
