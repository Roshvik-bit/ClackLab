"""
Dashboard view featuring master controls, status pills, visual keyboard, and live telemetry.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QComboBox, QFrame, QSizePolicy, QTextEdit
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPixmap, QTextCursor, QKeyEvent
from .keyboard_view import KeyboardView
from ..models import LatencyStats
from ..keyboard.key_mapping import keycode_to_char, is_backspace, is_shift, is_caps_lock

class PlaygroundTextEdit(QTextEdit):
    """
    Interactive Live Typing Test scratchpad for ClackLab.
    Captures keystrokes, provides acoustic feedback, triggers visual keycap illumination,
    and displays typing statistics in real-time.
    """
    key_typed = Signal(int, bool)  # keycode, is_pressed

    def keyPressEvent(self, event: QKeyEvent):
        keycode = event.nativeScanCode()
        if not event.isAutoRepeat():
            self.key_typed.emit(keycode, True)
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent):
        keycode = event.nativeScanCode()
        if not event.isAutoRepeat():
            self.key_typed.emit(keycode, False)
        super().keyReleaseEvent(event)

class DashboardView(QWidget):
    """Primary control hub for ClackLab."""

    # UI action signals
    master_toggled = Signal(bool)
    profile_selected = Signal(str)
    volume_changed = Signal(float)
    preview_clicked = Signal()
    key_clicked_down = Signal(int)
    key_clicked_up = Signal(int)
    permissions_requested = Signal()
    launch_at_login_toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.caps_lock_active = False
        self.shift_active = False
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(18, 18, 18, 18)

        # 1. Header Bar with Logo Badge
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        logo_label = QLabel(self)
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        logo_path = os.path.join(base_dir, "assets", "logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path).scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(pixmap)
            logo_label.setFixedSize(48, 48)
            header_layout.addWidget(logo_label)

        title_label = QLabel("ClackLab", self)
        title_label.setObjectName("HeaderLabel")
        title_label.setStyleSheet("font-size: 22px; font-weight: 800; color: #f8fafc;")

        subtitle_label = QLabel("Ultra-Low-Latency Virtual Mechanical Keyboard for macOS", self)
        subtitle_label.setObjectName("SubheaderLabel")

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)
        title_vbox.addWidget(title_label)
        title_vbox.addWidget(subtitle_label)
        header_layout.addLayout(title_vbox)
        header_layout.addStretch()

        # Master Toggle Button
        self.toggle_btn = QPushButton("ENABLED", self)
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(True)
        self.toggle_btn.setObjectName("PrimaryButton")
        self.toggle_btn.setFixedWidth(130)
        self.toggle_btn.setFixedHeight(38)
        self.toggle_btn.setStyleSheet("""
            QPushButton:checked {
                background-color: #10b981;
                border: 1px solid #34d399;
                color: #ffffff;
                font-weight: 800;
            }
            QPushButton:!checked {
                background-color: #ef4444;
                border: 1px solid #f87171;
                color: #ffffff;
                font-weight: 800;
            }
        """)
        self.toggle_btn.toggled.connect(self._on_toggle_clicked)
        header_layout.addWidget(self.toggle_btn)

        layout.addLayout(header_layout)

        # 2. Status Pills Bar
        status_bar = QHBoxLayout()
        status_bar.setSpacing(8)

        self.audio_pill = QLabel("● Audio Engine: Active (2.67ms buffer)", self)
        self.audio_pill.setStyleSheet("""
            background-color: #1a221f;
            color: #34d399;
            border: 1px solid #059669;
            padding: 6px 12px;
            border-radius: 14px;
            font-size: 11px;
            font-weight: 700;
        """)
        status_bar.addWidget(self.audio_pill)

        self.perm_pill = QPushButton("● macOS Accessibility: Trusted", self)
        self.perm_pill.setCursor(Qt.PointingHandCursor)
        self.perm_pill.clicked.connect(self._on_perm_pill_clicked)
        self.perm_pill.setStyleSheet("""
            QPushButton {
                background-color: #1a202c;
                color: #818cf8;
                border: 1px solid #4f46e5;
                padding: 6px 12px;
                border-radius: 14px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #262c3e;
            }
        """)
        status_bar.addWidget(self.perm_pill)

        self.device_pill = QLabel("Default Output Device", self)
        self.device_pill.setStyleSheet("""
            background-color: #1e222d;
            color: #cbd5e1;
            border: 1px solid #333947;
            padding: 6px 12px;
            border-radius: 14px;
            font-size: 11px;
            font-weight: 600;
        """)
        status_bar.addWidget(self.device_pill)

        self.login_pill = QPushButton("● Launch at Login: Enabled", self)
        self.login_pill.setCursor(Qt.PointingHandCursor)
        self.login_pill.clicked.connect(self._on_login_pill_clicked)
        status_bar.addWidget(self.login_pill)
        self._launch_at_login = True
        self.update_launch_at_login_status(True)

        status_bar.addStretch()

        # Quick preview button
        self.preview_btn = QPushButton("▶ Test Sound", self)
        self.preview_btn.setFixedHeight(30)
        self.preview_btn.clicked.connect(self.preview_clicked.emit)
        status_bar.addWidget(self.preview_btn)

        layout.addLayout(status_bar)

        # 3. Accessibility Onboarding Banner (shown when permission is required for global typing)
        self.perm_banner = QFrame(self)
        self.perm_banner.setStyleSheet("""
            QFrame {
                background-color: #241a10;
                border: 1px solid #d97706;
                border-radius: 10px;
            }
        """)
        pb_layout = QHBoxLayout(self.perm_banner)
        pb_layout.setContentsMargins(14, 10, 14, 10)
        pb_layout.setSpacing(12)

        pb_icon = QLabel("⚠️", self.perm_banner)
        pb_icon.setStyleSheet("font-size: 22px;")
        pb_layout.addWidget(pb_icon)

        pb_text_layout = QVBoxLayout()
        pb_text_layout.setSpacing(2)
        pb_title = QLabel("Global Keyboard Audio Requires macOS Accessibility", self.perm_banner)
        pb_title.setStyleSheet("font-weight: 800; color: #fbbf24; font-size: 13px;")
        pb_desc = QLabel(
            "Typing sounds currently only trigger while this window is focused. "
            "To hear mechanical typing sounds across Chrome, VS Code, Notes, and all other apps, enable ClackLab in macOS System Settings.",
            self.perm_banner
        )
        pb_desc.setStyleSheet("color: #e2e8f0; font-size: 11px;")
        pb_desc.setWordWrap(True)
        pb_text_layout.addWidget(pb_title)
        pb_text_layout.addWidget(pb_desc)
        pb_layout.addLayout(pb_text_layout, stretch=1)

        btn_vbox = QVBoxLayout()
        btn_vbox.setSpacing(6)

        self.perm_banner_btn = QPushButton("⚙ Open System Settings", self.perm_banner)
        self.perm_banner_btn.setCursor(Qt.PointingHandCursor)
        self.perm_banner_btn.setStyleSheet("""
            QPushButton {
                background-color: #d97706;
                color: #ffffff;
                font-weight: 800;
                font-size: 11px;
                padding: 6px 14px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #f59e0b;
            }
        """)
        self.perm_banner_btn.clicked.connect(self._on_perm_pill_clicked)
        btn_vbox.addWidget(self.perm_banner_btn)

        self.perm_restart_btn = QPushButton("🔄 Relaunch ClackLab", self.perm_banner)
        self.perm_restart_btn.setCursor(Qt.PointingHandCursor)
        self.perm_restart_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #38bdf8;
                font-weight: 700;
                font-size: 11px;
                padding: 6px 14px;
                border-radius: 6px;
                border: 1px solid #0284c7;
            }
            QPushButton:hover {
                background-color: #0369a1;
                color: #ffffff;
            }
        """)
        self.perm_restart_btn.clicked.connect(self._on_restart_clicked)
        btn_vbox.addWidget(self.perm_restart_btn)

        pb_layout.addLayout(btn_vbox)

        layout.addWidget(self.perm_banner)

        # 4. Interactive Visual Keyboard
        self.keyboard_view = KeyboardView(self)
        self.keyboard_view.key_clicked_down.connect(self._on_virtual_key_down)
        self.keyboard_view.key_clicked_up.connect(self.key_clicked_up.emit)
        layout.addWidget(self.keyboard_view)

        # 4. Quick Controls Row (Profile Selector & Master Volume)
        controls_frame = QFrame(self)
        controls_frame.setStyleSheet("""
            QFrame {
                background-color: #181a20;
                border: 1px solid #282c37;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        ctrl_layout = QHBoxLayout(controls_frame)
        ctrl_layout.setContentsMargins(12, 8, 12, 8)

        # Profile selection
        prof_label = QLabel("Active Switch:", self)
        prof_label.setStyleSheet("font-weight: 700; color: #cbd5e1;")
        ctrl_layout.addWidget(prof_label)

        self.profile_combo = QComboBox(self)
        self.profile_combo.setMinimumWidth(220)
        self.profile_combo.currentIndexChanged.connect(self._on_profile_changed)
        ctrl_layout.addWidget(self.profile_combo)

        ctrl_layout.addSpacing(30)

        # Volume slider
        vol_label = QLabel("Master Volume:", self)
        vol_label.setStyleSheet("font-weight: 700; color: #cbd5e1;")
        ctrl_layout.addWidget(vol_label)

        self.vol_slider = QSlider(Qt.Horizontal, self)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(85)
        self.vol_slider.setFixedWidth(160)
        self.vol_slider.valueChanged.connect(self._on_vol_changed)
        ctrl_layout.addWidget(self.vol_slider)

        self.vol_value_label = QLabel("85%", self)
        self.vol_value_label.setFixedWidth(40)
        self.vol_value_label.setStyleSheet("color: #94a3b8; font-weight: 600;")
        ctrl_layout.addWidget(self.vol_value_label)

        ctrl_layout.addStretch()

        # Telemetry metrics pill
        self.latency_pill = QLabel("Median: 0.12 ms | p95: 0.28 ms", self)
        self.latency_pill.setStyleSheet("""
            background-color: #131418;
            color: #38bdf8;
            padding: 5px 10px;
            border-radius: 6px;
            font-family: Menlo, Monaco, monospace;
            font-size: 11px;
            font-weight: 700;
        """)
        ctrl_layout.addWidget(self.latency_pill)

        layout.addWidget(controls_frame)

        # 5. Interactive Live Typing Playground & Acoustic Feedback Text Pad
        playground_frame = QFrame(self)
        playground_frame.setStyleSheet("""
            QFrame {
                background-color: #161820;
                border: 1px solid #282c37;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        pg_layout = QVBoxLayout(playground_frame)
        pg_layout.setContentsMargins(12, 10, 12, 10)
        pg_layout.setSpacing(8)

        # Header bar of playground
        pg_header = QHBoxLayout()
        pg_title = QLabel("📝 Live Typing Playground & Text Test Field", playground_frame)
        pg_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #cbd5e1;")
        pg_header.addWidget(pg_title)

        pg_header.addStretch()

        self.pg_stats = QLabel("Characters: 0 | Words: 0", playground_frame)
        self.pg_stats.setStyleSheet("font-size: 11px; color: #94a3b8; font-family: Menlo, Monaco, monospace;")
        pg_header.addWidget(self.pg_stats)

        self.sample_btn = QPushButton("Sample Text", playground_frame)
        self.sample_btn.setFixedHeight(24)
        self.sample_btn.setCursor(Qt.PointingHandCursor)
        self.sample_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e222d;
                color: #818cf8;
                border: 1px solid #4f46e5;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2a3042;
            }
        """)
        self.sample_btn.clicked.connect(self._load_sample_text)
        pg_header.addWidget(self.sample_btn)

        self.clear_btn = QPushButton("Clear", playground_frame)
        self.clear_btn.setFixedHeight(24)
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e222d;
                color: #94a3b8;
                border: 1px solid #333947;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2b303c;
                color: #f1f5f9;
            }
        """)
        self.clear_btn.clicked.connect(self._clear_playground_text)
        pg_header.addWidget(self.clear_btn)

        pg_layout.addLayout(pg_header)

        # Multi-line interactive text editor
        self.typing_edit = PlaygroundTextEdit(playground_frame)
        self.typing_edit.setFixedHeight(75)
        self.typing_edit.setPlaceholderText("⌨ Click any key on the virtual keyboard above or start typing on your physical keyboard...")
        self.typing_edit.setStyleSheet("""
            QTextEdit {
                background-color: #111319;
                color: #f1f5f9;
                border: 1px solid #2a2f3d;
                border-radius: 6px;
                padding: 8px 10px;
                font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", sans-serif;
                font-size: 13px;
                line-height: 1.4;
            }
            QTextEdit:focus {
                border: 1.5px solid #6366f1;
                background-color: #141720;
            }
        """)
        self.typing_edit.textChanged.connect(self._on_text_changed)
        self.typing_edit.key_typed.connect(self._on_playground_key_typed)
        pg_layout.addWidget(self.typing_edit)

        layout.addWidget(playground_frame)

    def set_profiles(self, profiles: list, active_id: str):
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        selected_idx = 0
        for idx, (p_id, p_name) in enumerate(profiles):
            self.profile_combo.addItem(p_name, p_id)
            if p_id == active_id:
                selected_idx = idx
        self.profile_combo.setCurrentIndex(selected_idx)
        self.profile_combo.blockSignals(False)

    def update_status(self, engine_active: bool, perm_trusted: bool, device_name: str):
        if engine_active:
            self.audio_pill.setText("● Audio Engine: Active (Low-Latency)")
            self.audio_pill.setStyleSheet("background-color: #14221c; color: #34d399; border: 1px solid #059669; padding: 6px 12px; border-radius: 14px; font-size: 11px; font-weight: 700;")
        else:
            self.audio_pill.setText("○ Audio Engine: Stopped")
            self.audio_pill.setStyleSheet("background-color: #271a1a; color: #f87171; border: 1px solid #dc2626; padding: 6px 12px; border-radius: 14px; font-size: 11px; font-weight: 700;")

        if perm_trusted:
            self.perm_banner.hide()
            self.perm_pill.setText("● macOS Accessibility: Trusted")
            self.perm_pill.setStyleSheet("background-color: #171d2b; color: #818cf8; border: 1px solid #4f46e5; padding: 6px 12px; border-radius: 14px; font-size: 11px; font-weight: 700;")
        else:
            self.perm_banner.show()
            self.perm_pill.setText("⚠ Accessibility: Permission Required")
            self.perm_pill.setStyleSheet("background-color: #2b2316; color: #fbbf24; border: 1px solid #d97706; padding: 6px 12px; border-radius: 14px; font-size: 11px; font-weight: 700;")

        self.device_pill.setText(f"Output: {device_name[:24]}")

    def update_latency_stats(self, stats: LatencyStats):
        self.latency_pill.setText(f"Median: {stats.median_ms} ms | p95: {stats.p95_ms} ms")

    def _on_toggle_clicked(self, checked: bool):
        self.toggle_btn.setText("ENABLED" if checked else "MUTED")
        self.master_toggled.emit(checked)

    def _on_profile_changed(self, index: int):
        prof_id = self.profile_combo.currentData()
        if prof_id:
            self.profile_selected.emit(prof_id)

    def _on_vol_changed(self, value: int):
        self.vol_value_label.setText(f"{value}%")
        self.volume_changed.emit(value / 100.0)

    def _on_perm_pill_clicked(self):
        from ..keyboard.permission_manager import PermissionManager
        PermissionManager.open_accessibility_settings()
        self.permissions_requested.emit()

    def _on_restart_clicked(self):
        from ..keyboard.permission_manager import PermissionManager
        PermissionManager.restart_app()

    def _on_login_pill_clicked(self):
        new_state = not getattr(self, "_launch_at_login", True)
        self.update_launch_at_login_status(new_state)
        self.launch_at_login_toggled.emit(new_state)

    def update_launch_at_login_status(self, enabled: bool):
        self._launch_at_login = enabled
        if enabled:
            self.login_pill.setText("● Launch at Login: Enabled")
            self.login_pill.setStyleSheet("""
                QPushButton {
                    background-color: #1a221f;
                    color: #34d399;
                    border: 1px solid #059669;
                    padding: 6px 12px;
                    border-radius: 14px;
                    font-size: 11px;
                    font-weight: 700;
                }
                QPushButton:hover {
                    background-color: #23312c;
                }
            """)
        else:
            self.login_pill.setText("○ Launch at Login: Disabled")
            self.login_pill.setStyleSheet("""
                QPushButton {
                    background-color: #22262f;
                    color: #94a3b8;
                    border: 1px solid #475569;
                    padding: 6px 12px;
                    border-radius: 14px;
                    font-size: 11px;
                    font-weight: 700;
                }
                QPushButton:hover {
                    background-color: #2d333f;
                }
            """)

    def _on_virtual_key_down(self, keycode: int):
        """Executed when user clicks a keycap on the on-screen virtual keyboard."""
        self.key_clicked_down.emit(keycode)
        self._handle_virtual_key_down(keycode)

    def _handle_virtual_key_down(self, keycode: int):
        # 1. Caps lock toggle
        if is_caps_lock(keycode):
            self.caps_lock_active = not self.caps_lock_active
            return

        # 2. Shift toggle
        if is_shift(keycode):
            self.shift_active = not self.shift_active
            return

        # 3. Backspace
        if is_backspace(keycode):
            cursor = self.typing_edit.textCursor()
            cursor.deletePreviousChar()
            self.typing_edit.setTextCursor(cursor)
            self.typing_edit.ensureCursorVisible()
            return

        # 4. Arrow navigation
        if keycode == 123:  # Left arrow
            cursor = self.typing_edit.textCursor()
            cursor.movePosition(QTextCursor.Left)
            self.typing_edit.setTextCursor(cursor)
            return
        elif keycode == 124:  # Right arrow
            cursor = self.typing_edit.textCursor()
            cursor.movePosition(QTextCursor.Right)
            self.typing_edit.setTextCursor(cursor)
            return

        # 5. Character insertion
        char = keycode_to_char(keycode, is_shift=self.shift_active, is_caps=self.caps_lock_active)
        if char:
            cursor = self.typing_edit.textCursor()
            cursor.insertText(char)
            self.typing_edit.setTextCursor(cursor)
            self.typing_edit.ensureCursorVisible()
            if self.shift_active:
                self.shift_active = False

    def _on_playground_key_typed(self, keycode: int, is_pressed: bool):
        # Visually highlight the keycap when typing in the playground
        self.keyboard_view.trigger_key(keycode, is_pressed)

    def _on_text_changed(self):
        text = self.typing_edit.toPlainText()
        chars = len(text)
        words = len(text.split()) if text.strip() else 0
        self.pg_stats.setText(f"Characters: {chars} | Words: {words}")

    def _load_sample_text(self):
        self.typing_edit.setPlainText("The quick brown fox jumps over the lazy dog.")
        cursor = self.typing_edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.typing_edit.setTextCursor(cursor)
        self.typing_edit.setFocus()

    def _clear_playground_text(self):
        self.typing_edit.clear()
        self.typing_edit.setFocus()
