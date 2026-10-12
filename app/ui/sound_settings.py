"""
Sound Settings panel providing controls for volume levels, acoustic variation, and key behaviors.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QCheckBox, QGroupBox, QPushButton, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, Signal
from ..settings import AppSettings

class SoundSettingsView(QWidget):
    """Configuration interface for acoustic tuning and typing behaviors."""

    settings_changed = Signal(dict)
    reset_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        header = QLabel("Sound & Typing Settings", self)
        header.setObjectName("HeaderLabel")
        header.setStyleSheet("font-size: 20px; font-weight: 800;")
        main_layout.addWidget(header)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget(scroll)
        c_layout = QVBoxLayout(container)
        c_layout.setSpacing(14)
        c_layout.setContentsMargins(0, 0, 0, 0)

        # --- 1. Volumes Group ---
        vol_group = QGroupBox("Acoustic Levels", container)
        v_layout = QVBoxLayout(vol_group)
        v_layout.setSpacing(10)

        # Key-Down Volume
        kd_row = QHBoxLayout()
        kd_label = QLabel("Key-Down Volume:", vol_group)
        kd_label.setFixedWidth(160)
        self.kd_slider = QSlider(Qt.Horizontal, vol_group)
        self.kd_slider.setRange(0, 100)
        self.kd_slider.setValue(100)
        self.kd_val = QLabel("100%", vol_group)
        self.kd_val.setFixedWidth(45)
        self.kd_slider.valueChanged.connect(lambda v: self._on_slider_changed("press_volume", v, self.kd_val))
        kd_row.addWidget(kd_label)
        kd_row.addWidget(self.kd_slider)
        kd_row.addWidget(self.kd_val)
        v_layout.addLayout(kd_row)

        # Key-Up Volume
        ku_row = QHBoxLayout()
        ku_label = QLabel("Key-Up (Release) Volume:", vol_group)
        ku_label.setFixedWidth(160)
        self.ku_slider = QSlider(Qt.Horizontal, vol_group)
        self.ku_slider.setRange(0, 100)
        self.ku_slider.setValue(70)
        self.ku_val = QLabel("70%", vol_group)
        self.ku_val.setFixedWidth(45)
        self.ku_slider.valueChanged.connect(lambda v: self._on_slider_changed("release_volume", v, self.ku_val))
        ku_row.addWidget(ku_label)
        ku_row.addWidget(self.ku_slider)
        ku_row.addWidget(self.ku_val)
        v_layout.addLayout(ku_row)

        c_layout.addWidget(vol_group)

        # --- 2. Acoustic Variation Group ---
        var_group = QGroupBox("Acoustic Realism & Variation", container)
        va_layout = QVBoxLayout(var_group)
        va_layout.setSpacing(10)

        self.cb_randomize = QCheckBox("Enable Sample Variation (Anti-Repetition Round-Robin)", var_group)
        self.cb_randomize.setChecked(True)
        self.cb_randomize.toggled.connect(lambda c: self.settings_changed.emit({"randomize_samples": c}))
        va_layout.addWidget(self.cb_randomize)

        self.cb_pitch = QCheckBox("Enable Subtle Micro-Pitch Variation (Simulates Real Finger Dynamics)", var_group)
        self.cb_pitch.setChecked(True)
        self.cb_pitch.toggled.connect(lambda c: self.settings_changed.emit({"pitch_variation_enabled": c}))
        va_layout.addWidget(self.cb_pitch)

        # Pitch variation range slider
        pv_row = QHBoxLayout()
        pv_label = QLabel("Pitch Variation Amount:", var_group)
        pv_label.setFixedWidth(160)
        self.pv_slider = QSlider(Qt.Horizontal, var_group)
        self.pv_slider.setRange(1, 8)  # 1% to 8%
        self.pv_slider.setValue(3)
        self.pv_val = QLabel("±3%", var_group)
        self.pv_val.setFixedWidth(45)
        self.pv_slider.valueChanged.connect(lambda v: self._on_pitch_amount_changed(v))
        pv_row.addWidget(pv_label)
        pv_row.addWidget(self.pv_slider)
        pv_row.addWidget(self.pv_val)
        va_layout.addLayout(pv_row)

        c_layout.addWidget(var_group)

        # --- 3. Key Typing Behaviors ---
        beh_group = QGroupBox("Typing & Key Event Behaviors", container)
        b_layout = QVBoxLayout(beh_group)
        b_layout.setSpacing(10)

        self.cb_key_up = QCheckBox("Play Key-Up (Release) Sounds", beh_group)
        self.cb_key_up.setChecked(True)
        self.cb_key_up.toggled.connect(lambda c: self.settings_changed.emit({"play_key_up": c}))
        b_layout.addWidget(self.cb_key_up)

        self.cb_stabilizers = QCheckBox("Play Stabilizer Acoustics for Large Keys (Space, Enter, Backspace)", beh_group)
        self.cb_stabilizers.setChecked(True)
        self.cb_stabilizers.toggled.connect(lambda c: self.settings_changed.emit({"play_stabilizers": c}))
        b_layout.addWidget(self.cb_stabilizers)

        self.cb_modifiers = QCheckBox("Play Sounds for Modifier Keys (Shift, Cmd, Option, Ctrl)", beh_group)
        self.cb_modifiers.setChecked(True)
        self.cb_modifiers.toggled.connect(lambda c: self.settings_changed.emit({"play_modifiers": c}))
        b_layout.addWidget(self.cb_modifiers)

        self.cb_repeats = QCheckBox("Play Sounds on Held Key Repeats (Disabled by default for natural typing feel)", beh_group)
        self.cb_repeats.setChecked(False)
        self.cb_repeats.toggled.connect(lambda c: self.settings_changed.emit({"play_key_repeats": c}))
        b_layout.addWidget(self.cb_repeats)

        self.cb_visual = QCheckBox("Show Visual Keyboard Keypress Animation", beh_group)
        self.cb_visual.setChecked(True)
        self.cb_visual.toggled.connect(lambda c: self.settings_changed.emit({"visual_keyboard_feedback": c}))
        b_layout.addWidget(self.cb_visual)

        c_layout.addWidget(beh_group)

        # --- 4. macOS System & Startup Integration ---
        sys_group = QGroupBox("System & Startup", container)
        s_layout = QVBoxLayout(sys_group)
        s_layout.setSpacing(10)

        self.cb_launch_login = QCheckBox("Launch ClackLab Automatically at macOS Login", sys_group)
        self.cb_launch_login.setChecked(True)
        self.cb_launch_login.toggled.connect(lambda c: self.settings_changed.emit({"launch_at_login": c}))
        s_layout.addWidget(self.cb_launch_login)

        c_layout.addWidget(sys_group)

        # Reset button
        btn_row = QHBoxLayout()
        self.reset_btn = QPushButton("Reset All Sound Settings to Defaults", container)
        self.reset_btn.clicked.connect(self.reset_requested.emit)
        btn_row.addStretch()
        btn_row.addWidget(self.reset_btn)
        c_layout.addLayout(btn_row)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def load_settings(self, settings: AppSettings):
        self.kd_slider.setValue(int(settings.press_volume * 100))
        self.ku_slider.setValue(int(settings.release_volume * 100))
        self.cb_randomize.setChecked(settings.randomize_samples)
        self.cb_pitch.setChecked(settings.pitch_variation_enabled)
        self.pv_slider.setValue(int(settings.pitch_variation_amount * 100))
        self.cb_key_up.setChecked(settings.play_key_up)
        self.cb_stabilizers.setChecked(settings.play_stabilizers)
        self.cb_modifiers.setChecked(settings.play_modifiers)
        self.cb_repeats.setChecked(settings.play_key_repeats)
        self.cb_visual.setChecked(settings.visual_keyboard_feedback)
        self.cb_launch_login.setChecked(settings.launch_at_login)

    def _on_slider_changed(self, key: str, val: int, label: QLabel):
        label.setText(f"{val}%")
        self.settings_changed.emit({key: val / 100.0})

    def _on_pitch_amount_changed(self, val: int):
        self.pv_val.setText(f"±{val}%")
        self.settings_changed.emit({"pitch_variation_amount": val / 100.0})
