from PySide6.QtCore import QPointF, QRect, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from daisy_pet.bubble import SpeechBubble


def test_click_dismisses_bubble(qapp):
    bubble = SpeechBubble()
    bubble.show_message("Have a sip!", QRect(100, 100, 192, 208), 10)
    qapp.processEvents()
    assert bubble.isVisible()

    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(5, 5),
        QPointF(5, 5),
        QPointF(5, 5),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(bubble, event)
    assert not bubble.isVisible()
