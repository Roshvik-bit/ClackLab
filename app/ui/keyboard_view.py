"""
Interactive visual 60% Mac keyboard representation for ClackLab.
Highlights keycaps on keypress with mechanical travel animations.
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt, QTimer, Signal
from typing import Dict, Tuple

# Key layout definition: (Key Label, Keycode, Width Multiplier)
KEYBOARD_ROWS = [
    # Row 0
    [
        ("ESC", 53, 1.0), ("1", 18, 1.0), ("2", 19, 1.0), ("3", 20, 1.0),
        ("4", 21, 1.0), ("5", 23, 1.0), ("6", 22, 1.0), ("7", 26, 1.0),
        ("8", 28, 1.0), ("9", 25, 1.0), ("0", 29, 1.0), ("-", 27, 1.0),
        ("=", 24, 1.0), ("DELETE", 51, 1.8)
    ],
    # Row 1
    [
        ("TAB", 48, 1.5), ("Q", 12, 1.0), ("W", 13, 1.0), ("E", 14, 1.0),
        ("R", 15, 1.0), ("T", 17, 1.0), ("Y", 16, 1.0), ("U", 32, 1.0),
        ("I", 34, 1.0), ("O", 31, 1.0), ("P", 35, 1.0), ("[", 33, 1.0),
        ("]", 30, 1.0), ("\\", 42, 1.3)
    ],
    # Row 2
    [
        ("CAPS", 57, 1.8), ("A", 0, 1.0), ("S", 1, 1.0), ("D", 2, 1.0),
        ("F", 3, 1.0), ("G", 5, 1.0), ("H", 4, 1.0), ("J", 38, 1.0),
        ("K", 40, 1.0), ("L", 37, 1.0), (";", 41, 1.0), ("'", 39, 1.0),
        ("RETURN", 36, 2.0)
    ],
    # Row 3
    [
        ("SHIFT", 56, 2.3), ("Z", 6, 1.0), ("X", 7, 1.0), ("C", 8, 1.0),
        ("V", 9, 1.0), ("B", 11, 1.0), ("N", 45, 1.0), ("M", 46, 1.0),
        (",", 43, 1.0), (".", 47, 1.0), ("/", 44, 1.0), ("SHIFT", 60, 2.5)
    ],
    # Row 4
    [
        ("FN", 63, 1.0), ("CTRL", 59, 1.2), ("OPT", 58, 1.2), ("CMD", 55, 1.4),
        ("SPACE", 49, 5.8),
        ("CMD", 54, 1.4), ("OPT", 61, 1.2), ("◀", 123, 1.0), ("▲", 126, 1.0),
        ("▼", 125, 1.0), ("▶", 124, 1.0)
    ]
]

class KeyCapWidget(QFrame):
    """Individual mechanical keycap widget with interactive click and mechanical travel depth styling."""

    key_pressed = Signal(int)
    key_released = Signal(int)

    def __init__(self, label: str, keycode: int, width_mult: float = 1.0, parent=None):
        super().__init__(parent)
        self.keycode = keycode
        self.label_text = label
        self.is_pressed = False

        base_unit = 38
        self.setFixedWidth(int(base_unit * width_mult))
        self.setFixedHeight(38)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setAlignment(Qt.AlignCenter)

        self.label = QLabel(label, self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("font-size: 10px; font-weight: 700; color: #cbd5e1;")
        layout.addWidget(self.label)

        self.set_active_style(False)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.set_active_style(True)
            self.key_pressed.emit(self.keycode)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.set_active_style(False)
            self.key_released.emit(self.keycode)
        super().mouseReleaseEvent(event)

    def set_active_style(self, pressed: bool):
        self.is_pressed = pressed
        if pressed:
            self.setStyleSheet("""
                QFrame {
                    background-color: #6366f1;
                    border: 1px solid #818cf8;
                    border-radius: 5px;
                    margin-top: 2px;
                }
            """)
            self.label.setStyleSheet("font-size: 10px; font-weight: 800; color: #ffffff;")
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #20222a;
                    border: 1px solid #303542;
                    border-bottom: 3px solid #14151b;
                    border-radius: 5px;
                    margin-top: 0px;
                }
                QFrame:hover {
                    background-color: #2b2e3a;
                    border: 1px solid #6366f1;
                }
            """)
            self.label.setStyleSheet("font-size: 10px; font-weight: 700; color: #94a3b8;")

class KeyboardView(QWidget):
    """Visual keyboard panel containing all interactive keycaps."""

    key_clicked_down = Signal(int)
    key_clicked_up = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.key_map: Dict[int, KeyCapWidget] = {}
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(12, 12, 12, 12)

        container = QFrame(self)
        container.setStyleSheet("""
            QFrame {
                background-color: #16171d;
                border: 2px solid #272a34;
                border-radius: 12px;
                padding: 4px;
            }
        """)
        c_layout = QVBoxLayout(container)
        c_layout.setSpacing(4)
        c_layout.setContentsMargins(8, 8, 8, 8)

        for row_keys in KEYBOARD_ROWS:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(4)
            row_layout.setContentsMargins(0, 0, 0, 0)

            for label, keycode, mult in row_keys:
                keycap = KeyCapWidget(label, keycode, mult, self)
                keycap.key_pressed.connect(self.key_clicked_down.emit)
                keycap.key_released.connect(self.key_clicked_up.emit)
                row_layout.addWidget(keycap)
                self.key_map[keycode] = keycap

            c_layout.addLayout(row_layout)

        main_layout.addWidget(container)

    def trigger_key(self, keycode: int, is_pressed: bool):
        """Highlights keycap on press and releases on key up, with auto-reset safety."""
        if keycode in self.key_map:
            keycap = self.key_map[keycode]
            keycap.set_active_style(is_pressed)
            if is_pressed:
                # 350ms safety timer to ensure keys never remain permanently stuck
                QTimer.singleShot(350, lambda: keycap.set_active_style(False) if keycap.is_pressed else None)

