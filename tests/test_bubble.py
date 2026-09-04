from PySide6.QtCore import QPointF, QRect, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

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


def test_actionable_click_acknowledges(qapp):
    bubble = SpeechBubble()
    seen = []
    bubble.acknowledged.connect(lambda: seen.append(True))
    bubble.show_message("Have a sip!", QRect(100, 100, 192, 208), 10, True)
    qapp.processEvents()
    QTest.mousePress(bubble, Qt.MouseButton.LeftButton)
    assert seen == [True]
    assert not bubble.isVisible()


def test_actionable_timeout_ignores(qapp):
    bubble = SpeechBubble()
    seen = []
    bubble.ignored.connect(lambda: seen.append(True))
    bubble.show_message("Have a sip!", QRect(100, 100, 192, 208), 1, True)
    QTest.qWait(1100)
    assert seen == [True]
    assert not bubble.isVisible()


def test_non_actionable_click_emits_neither(qapp):
    bubble = SpeechBubble()
    ack, ignored = [], []
    bubble.acknowledged.connect(lambda: ack.append(True))
    bubble.ignored.connect(lambda: ignored.append(True))
    bubble.show_message("Hello", QRect(100, 100, 192, 208), 10)
    QTest.mousePress(bubble, Qt.MouseButton.LeftButton)
    assert ack == []
    assert ignored == []


def test_choice_bubble_emits_clicked_label(qapp):
    bubble = SpeechBubble()
    choices = []
    bubble.chose.connect(choices.append)
    bubble.show_choice(
        "Close this tab?",
        QRect(100, 100, 192, 208),
        10,
        ("Keep it", "Next"),
    )
    qapp.processEvents()
    assert len(bubble._choice_buttons) == 2
    bubble._choice_buttons[1].click()
    assert choices == ["Next"]
    assert not bubble.isVisible()


def test_choice_bubble_expiry_emits_ignored(qapp):
    bubble = SpeechBubble()
    ignored = []
    bubble.ignored.connect(lambda: ignored.append(True))
    bubble.show_choice(
        "Close this tab?",
        QRect(100, 100, 192, 208),
        10,
        ("Keep it", "Next"),
    )
    bubble._expire()
    assert ignored == [True]


def test_choice_bubble_replaces_buttons_and_wraps_long_text(qapp):
    bubble = SpeechBubble()
    bubble.show_choice(
        "A long first prompt that takes more than one line to render correctly.",
        QRect(100, 100, 192, 208),
        10,
        ("Show me", "Later"),
    )
    bubble.show_choice(
        'Close "Jenkins - build #4211 - console output"? Press Ctrl+W — '
        "or Keep it and I'll ask tomorrow.",
        QRect(100, 100, 192, 208),
        10,
        ("Keep it", "Next"),
    )
    qapp.processEvents()

    assert len(bubble._choice_buttons) == 2
    assert [button.text() for button in bubble._choice_buttons] == [
        "Keep it",
        "Next",
    ]
    assert bubble._label.height() >= bubble._label.heightForWidth(236)
