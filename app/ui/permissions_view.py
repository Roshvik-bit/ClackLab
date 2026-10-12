"""
macOS Permissions onboarding, step-by-step guide, and privacy pledge view.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFrame
)
from PySide6.QtCore import Signal
from ..keyboard.permission_manager import PermissionManager

class PermissionsView(QWidget):
    """Explains macOS privacy requirements, checks accessibility status, and displays privacy guarantees."""

    verify_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        header = QLabel("macOS Permissions & Privacy", self)
        header.setObjectName("HeaderLabel")
        header.setStyleSheet("font-size: 20px; font-weight: 800;")
        layout.addWidget(header)

        # 1. Permission Status Card
        self.status_frame = QFrame(self)
        self.status_frame.setObjectName("StatusFrame")
        sf_layout = QVBoxLayout(self.status_frame)
        sf_layout.setContentsMargins(16, 14, 16, 14)
        sf_layout.setSpacing(8)

        self.status_title = QLabel("● Accessibility Permission Status: Checking...", self.status_frame)
        self.status_title.setStyleSheet("font-size: 15px; font-weight: 800;")
        sf_layout.addWidget(self.status_title)

        self.status_desc = QLabel(
            "macOS requires explicit user authorization via Accessibility to allow background keyboard event listening (CGEventTap) "
            "so mechanical sounds can trigger while you type in other applications.",
            self.status_frame
        )
        self.status_desc.setWordWrap(True)
        self.status_desc.setStyleSheet("color: #cbd5e1; font-size: 12px; line-height: 1.4;")
        sf_layout.addWidget(self.status_desc)

        # Buttons
        btn_row = QHBoxLayout()
        self.open_settings_btn = QPushButton("⚙ Open macOS System Settings", self.status_frame)
        self.open_settings_btn.setObjectName("PrimaryButton")
        self.open_settings_btn.clicked.connect(PermissionManager.open_accessibility_settings)
        btn_row.addWidget(self.open_settings_btn)

        self.verify_btn = QPushButton("✓ Verify Permission Now", self.status_frame)
        self.verify_btn.clicked.connect(self.verify_requested.emit)
        btn_row.addWidget(self.verify_btn)

        btn_row.addStretch()
        sf_layout.addLayout(btn_row)
        layout.addWidget(self.status_frame)

        # 2. Step-by-Step Instructions
        guide_group = QGroupBox("Manual Authorization Instructions", self)
        gg_layout = QVBoxLayout(guide_group)
        gg_layout.setSpacing(8)

        steps = [
            "1. Click the 'Open macOS System Settings' button above.",
            "2. In System Settings, navigate to Privacy & Security > Accessibility.",
            "3. Locate 'ClackLab' (or your Terminal / Python environment) in the list.",
            "4. Toggle the switch to ON.",
            "5. If prompted, restart or return to ClackLab and click 'Verify Permission Now'."
        ]
        for step in steps:
            lbl = QLabel(step, guide_group)
            lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
            gg_layout.addWidget(lbl)

        layout.addWidget(guide_group)

        # 3. Privacy Guarantee
        priv_group = QGroupBox("Privacy & Local Security Guarantee", self)
        pg_layout = QVBoxLayout(priv_group)
        pg_layout.setSpacing(8)

        priv_items = [
            ("🔒 Zero Text Capture:", "ClackLab only reads virtual keycode numbers to trigger sound categories. It never logs, records, inspects, or saves the words you type."),
            ("🌐 100% Offline Operation:", "The application never establishes background network connections. All sound playback happens entirely locally in RAM."),
            ("🎙 Zero Microphone Access:", "ClackLab is an audio output synthesizer. It never requests or accesses your microphone or input devices."),
            ("🚫 No Keystroke Interception:", "The event monitor runs strictly in ListenOnly mode. It cannot suppress, intercept, delay, or modify your typing.")
        ]
        for title, detail in priv_items:
            row = QHBoxLayout()
            t_lbl = QLabel(title, priv_group)
            t_lbl.setFixedWidth(180)
            t_lbl.setStyleSheet("font-weight: 700; color: #34d399;")
            d_lbl = QLabel(detail, priv_group)
            d_lbl.setWordWrap(True)
            d_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
            row.addWidget(t_lbl)
            row.addWidget(d_lbl)
            pg_layout.addLayout(row)

        layout.addWidget(priv_group)
        layout.addStretch()

        self.update_status(PermissionManager.is_accessibility_granted())

    def update_status(self, is_granted: bool):
        if is_granted:
            self.status_title.setText("● Accessibility Permission: GRANTED (Active)")
            self.status_title.setStyleSheet("font-size: 15px; font-weight: 800; color: #34d399;")
            self.status_frame.setStyleSheet("""
                QFrame#StatusFrame {
                    background-color: #14221c;
                    border: 2px solid #059669;
                    border-radius: 10px;
                }
            """)
        else:
            self.status_title.setText("⚠ Accessibility Permission: ACTION REQUIRED")
            self.status_title.setStyleSheet("font-size: 15px; font-weight: 800; color: #fbbf24;")
            self.status_frame.setStyleSheet("""
                QFrame#StatusFrame {
                    background-color: #2b2316;
                    border: 2px solid #d97706;
                    border-radius: 10px;
                }
            """)
