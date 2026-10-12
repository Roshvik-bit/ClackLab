"""
Unit tests for interactive on-screen key clicking and window keypress handling.
"""

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPointF, QEvent
from PySide6.QtGui import QMouseEvent, QKeyEvent
from app.ui.keyboard_view import KeyCapWidget, KeyboardView
from app.ui.dashboard import DashboardView

@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

def test_keycap_interactive_mouse_clicks(qapp):
    keycap = KeyCapWidget(label="A", keycode=0)
    assert keycap.cursor().shape() == Qt.PointingHandCursor
    assert keycap.is_pressed is False

    clicked_down = []
    clicked_up = []
    keycap.key_pressed.connect(lambda kc: clicked_down.append(kc))
    keycap.key_released.connect(lambda kc: clicked_up.append(kc))

    # Mouse press
    press_ev = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(5, 5),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    keycap.mousePressEvent(press_ev)
    assert keycap.is_pressed is True
    assert clicked_down == [0]

    # Mouse release
    release_ev = QMouseEvent(
        QEvent.Type.MouseButtonRelease,
        QPointF(5, 5),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier
    )
    keycap.mouseReleaseEvent(release_ev)
    assert keycap.is_pressed is False
    assert clicked_up == [0]

def test_keyboard_view_click_signals(qapp):
    kb = KeyboardView()
    down_keys = []
    up_keys = []
    kb.key_clicked_down.connect(lambda kc: down_keys.append(kc))
    kb.key_clicked_up.connect(lambda kc: up_keys.append(kc))

    # Keycode 49 is Space
    assert 49 in kb.key_map
    space_key = kb.key_map[49]

    press_ev = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(5, 5),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    space_key.mousePressEvent(press_ev)
    assert down_keys == [49]

    release_ev = QMouseEvent(
        QEvent.Type.MouseButtonRelease,
        QPointF(5, 5),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier
    )
    space_key.mouseReleaseEvent(release_ev)
    assert up_keys == [49]

def test_dashboard_view_signals_and_perm_pill(qapp):
    dash = DashboardView()
    assert dash.perm_pill is not None
    assert dash.keyboard_view is not None

    down_events = []
    dash.key_clicked_down.connect(lambda kc: down_events.append(kc))

    # Trigger click on Escape (keycode 53)
    esc_key = dash.keyboard_view.key_map[53]
    press_ev = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(5, 5),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    esc_key.mousePressEvent(press_ev)
    assert down_events == [53]
