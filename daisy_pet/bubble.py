from PySide6.QtCore import QRect, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QGuiApplication,
    QLinearGradient,
    QPainter,
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
        self._label.setStyleSheet("color: #17202a; background: transparent;")
        self._label.setFont(QFont("Segoe UI", 10))
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 9, 12, 9)
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
                "color: #17202a; background: #e8f0f7; "
                "border: 1px solid #b7c9d6; border-radius: 5px; padding: 4px 8px;"
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
        left, top, right, bottom = 12, 9, 12, 9
        if self._tail_below:
            top += 16
        else:
            bottom += 16
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
        width = self.width()
        height = self.height()
        tail = 16
        body_top = tail if self._tail_below else 0
        body_bottom = height - (0 if self._tail_below else tail)
        body = QRectF(2, body_top + 2, width - 4, body_bottom - body_top - 4)
        path = QPainterPath()
        path.addRoundedRect(body, 12, 12)
        for center_x in (body.left() + 22, body.center().x(), body.right() - 22):
            path = path.united(
                self._cloud_lump(center_x, body.top(), top=True)
            )
            path = path.united(
                self._cloud_lump(center_x, body.bottom(), top=False)
            )

        center_x = body.center().x()
        if self._tail_below:
            base_y, tip_y = body.top() + 2, 2
        else:
            base_y, tip_y = body.bottom() - 2, height - 2
        tail_path = QPainterPath()
        tail_path.moveTo(center_x - 9, base_y)
        tail_path.quadTo(center_x, tip_y, center_x + 9, base_y)
        tail_path.quadTo(center_x, base_y + (2 if self._tail_below else -2), center_x - 9, base_y)
        path = path.united(tail_path)

        gradient = QLinearGradient(0, 0, 0, height)
        gradient.setColorAt(0, QColor("#ffffff"))
        gradient.setColorAt(1, QColor("#e6f2fb"))
        painter.setPen(QPen(QColor("#6ba3cf"), 2))
        painter.setBrush(gradient)
        painter.drawPath(path)

    @staticmethod
    def _cloud_lump(center_x: float, edge_y: float, top: bool) -> QPainterPath:
        radius_x, radius_y = 14, 10
        center_y = edge_y + (radius_y - 1 if top else -(radius_y - 1))
        ellipse = QRectF(
            center_x - radius_x,
            center_y - radius_y,
            radius_x * 2,
            radius_y * 2,
        )
        path = QPainterPath()
        path.addEllipse(ellipse)
        return path

    def mousePressEvent(self, event) -> None:
        if self._actionable and not self._clicked:
            self._clicked = True
            self.acknowledged.emit()
        self.hide()
        super().mousePressEvent(event)
