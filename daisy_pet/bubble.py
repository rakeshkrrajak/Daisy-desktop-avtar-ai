from PySide6.QtCore import QRect, Qt, QTimer, Signal
from PySide6.QtGui import QFont, QGuiApplication, QPainter
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class SpeechBubble(QWidget):
    acknowledged = Signal()
    ignored = Signal()

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
        self._label.setMaximumWidth(236)
        self._label.setStyleSheet("color: #17202a; background: transparent;")
        self._label.setFont(QFont("Segoe UI", 10))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.addWidget(self._label)
        self._hide_timer: QTimer | None = None
        self._actionable = False
        self._clicked = False

    def show_message(
        self, text: str, near: QRect, seconds: int, actionable: bool = False
    ) -> None:
        self._actionable = actionable
        self._clicked = False
        if actionable:
            text = f"{text}\nClick me once you've had a sip"
        self._label.setText(text)
        self._label.adjustSize()
        self.adjustSize()
        screen = (
            QGuiApplication.screenAt(near.center())
            or self.screen()
            or QGuiApplication.primaryScreen()
        )
        area = screen.availableGeometry() if screen else QRect(0, 0, 1024, 768)
        x = near.center().x() - self.width() // 2
        x = max(area.left() + 4, min(x, area.right() - self.width() - 4))
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

    def set_message_text(self, text: str) -> None:
        if self._actionable:
            text = f"{text}\nClick me once you've had a sip"
        self._label.setText(text)
        self._label.adjustSize()
        self.adjustSize()

    def _expire(self) -> None:
        if self._actionable and not self._clicked:
            self.ignored.emit()
        self.hide()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.GlobalColor.lightGray)
        painter.setBrush(Qt.GlobalColor.white)
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 10, 10)

    def mousePressEvent(self, event) -> None:
        if self._actionable and not self._clicked:
            self._clicked = True
            self.acknowledged.emit()
        self.hide()
        super().mousePressEvent(event)
