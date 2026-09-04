from PySide6.QtCore import QRect, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QGuiApplication,
    QPainter,
    QLinearGradient,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


TAIL_HEIGHT = 32
BODY_INSET = 4
SHADOW_OFFSET = 6
OUTLINE_WIDTH = 4
CORNER = 22
FILL_TOP = "#fff6d6"
FILL_BOTTOM = "#ffe082"
OUTLINE = "#20242b"
INK = "#20242b"


class SpeechBubble(QWidget):
    acknowledged = Signal()
    ignored = Signal()
    chose = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._label = QLabel(self)
        self._label.setWordWrap(True)
        self._label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._label.setFixedWidth(236)
        self._label.setStyleSheet(f"color: {INK}; background: transparent;")
        font = QFont("Segoe UI", 10)
        font.setBold(True)
        self._label.setFont(font)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(
            20, 18, 20 + SHADOW_OFFSET, 18 + SHADOW_OFFSET
        )
        self._layout.addWidget(self._label)
        self._choice_layout = QHBoxLayout()
        self._layout.addLayout(self._choice_layout)
        self._choice_buttons: list[QPushButton] = []
        self._choice_layout.setEnabled(False)
        self._hide_timer: QTimer | None = None
        self._actionable = False
        self._choice_mode = False
        self._clicked = False
        self._tail_below = False

    def show_message(
        self, text: str, near: QRect, seconds: int, actionable: bool = False
    ) -> None:
        self._clear_choices()
        self._actionable = actionable
        self._choice_mode = False
        self._clicked = False
        if actionable:
            text = f"{text}\nClick me once you've had a sip"
        self._label.setText(text)
        self._label.setFixedHeight(self._label.heightForWidth(236))
        self.adjustSize()
        self._show_near(near, seconds)

    def show_choice(
        self,
        text: str,
        near: QRect,
        seconds: int,
        choices: tuple[str, str],
    ) -> None:
        self._actionable = False
        self._choice_mode = True
        self._clicked = False
        self._label.setText(text)
        self._label.setFixedHeight(self._label.heightForWidth(236))
        self._clear_choices()
        for choice in choices:
            button = QPushButton(choice, self)
            button.setStyleSheet(
                f"color: {INK}; background: #ffffff; "
                f"border: 3px solid {OUTLINE}; border-radius: 14px; "
                "padding: 5px 12px; font-weight: bold;"
            )
            button.clicked.connect(
                lambda _checked=False, label=choice: self._choose(label)
            )
            self._choice_layout.addWidget(button)
            self._choice_buttons.append(button)
        self._choice_layout.setEnabled(True)
        self.adjustSize()
        self._show_near(near, seconds)

    def _clear_choices(self) -> None:
        for button in self._choice_buttons:
            self._choice_layout.removeWidget(button)
            button.setParent(None)
            button.deleteLater()
        self._choice_buttons.clear()
        self._choice_layout.setEnabled(False)

    def _show_near(self, near: QRect, seconds: int) -> None:
        screen = (
            QGuiApplication.screenAt(near.center())
            or self.screen()
            or QGuiApplication.primaryScreen()
        )
        area = screen.availableGeometry() if screen else QRect(0, 0, 1024, 768)
        x = near.center().x() - self.width() // 2
        x = max(area.left() + 4, min(x, area.right() - self.width() - 4))
        above = near.top() - self.height() - 8
        self._tail_below = above < area.top()
        left, top, right, bottom = 20, 18, 20 + SHADOW_OFFSET, 18 + SHADOW_OFFSET
        if self._tail_below:
            top += TAIL_HEIGHT
        else:
            bottom += TAIL_HEIGHT
        self._layout.setContentsMargins(left, top, right, bottom)
        self.adjustSize()
        above = near.top() - self.height() - 8
        y = above if above >= area.top() else near.bottom() + 8
        self.move(x, y)
        self.show()
        self.raise_()
        if self._hide_timer is not None:
            self._hide_timer.stop()
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._expire)
        self._hide_timer.start(max(1, seconds) * 1000)

    def _choose(self, choice: str) -> None:
        self._actionable = False
        if self._hide_timer is not None:
            self._hide_timer.stop()
        self.hide()
        self.chose.emit(choice)

    def set_message_text(self, text: str) -> None:
        if self._actionable:
            text = f"{text}\nClick me once you've had a sip"
        self._label.setText(text)
        self._label.setFixedHeight(self._label.heightForWidth(236))
        self.adjustSize()

    def _expire(self) -> None:
        if self._actionable and not self._clicked:
            self.ignored.emit()
        elif self._choice_mode:
            self.ignored.emit()
        self._choice_mode = False
        self.hide()

    def hide(self) -> None:
        if self._hide_timer is not None:
            self._hide_timer.stop()
        super().hide()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        height = self.height()
        body_top = (TAIL_HEIGHT if self._tail_below else 0) + BODY_INSET
        body_bottom = (
            height - (0 if self._tail_below else TAIL_HEIGHT) - BODY_INSET
        )
        body = QRectF(
            BODY_INSET,
            body_top,
            self.width() - 2 * BODY_INSET - SHADOW_OFFSET,
            body_bottom - body_top - SHADOW_OFFSET,
        )
        path = QPainterPath()
        path.addRoundedRect(body, CORNER, CORNER)
        path = path.united(self._tail(body))

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(OUTLINE))
        painter.drawPath(path.translated(SHADOW_OFFSET, SHADOW_OFFSET))
        gradient = QLinearGradient(0, body.top(), 0, body.bottom())
        gradient.setColorAt(0, QColor(FILL_TOP))
        gradient.setColorAt(1, QColor(FILL_BOTTOM))
        painter.setPen(QPen(QColor(OUTLINE), OUTLINE_WIDTH))
        painter.setBrush(gradient)
        painter.drawPath(path)

    def _tail(self, body: QRectF) -> QPainterPath:
        center_x = body.center().x()
        if self._tail_below:
            base_y = body.top() + 2
            tip_y = base_y - TAIL_HEIGHT
        else:
            base_y = body.bottom() - 2
            tip_y = base_y + TAIL_HEIGHT
        path = QPainterPath()
        path.moveTo(center_x - 34, base_y)
        path.lineTo(center_x - 6, tip_y)
        path.lineTo(center_x + 20, base_y)
        path.closeSubpath()
        return path

    def mousePressEvent(self, event) -> None:
        if self._actionable and not self._clicked:
            self._clicked = True
            self.acknowledged.emit()
        self.hide()
        super().mousePressEvent(event)
