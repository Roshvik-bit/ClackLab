"""
Audio output devices and low-latency buffer configuration view.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QGroupBox, QPushButton, QFrame
)
from PySide6.QtCore import Signal
from typing import List, Dict, Any, Optional
from ..audio.audio_devices import AudioDeviceManager

class AudioDevicesView(QWidget):
    """Manages audio output device selection and buffer size configuration."""

    device_selected = Signal(int)  # device index
    buffer_size_selected = Signal(int)  # frame count
    test_sound_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        header = QLabel("Audio Output & Latency Configuration", self)
        header.setObjectName("HeaderLabel")
        header.setStyleSheet("font-size: 20px; font-weight: 800;")
        layout.addWidget(header)

        sub = QLabel("Select the target macOS audio output interface and configure low-latency PortAudio buffers.", self)
        sub.setObjectName("SubheaderLabel")
        layout.addWidget(sub)

        # 1. Device Selection Group
        dev_group = QGroupBox("Target Output Interface", self)
        dg_layout = QVBoxLayout(dev_group)
        dg_layout.setSpacing(12)

        d_row = QHBoxLayout()
        d_label = QLabel("Output Device:", dev_group)
        d_label.setFixedWidth(140)
        self.device_combo = QComboBox(dev_group)
        self.device_combo.setMinimumWidth(320)
        self.device_combo.currentIndexChanged.connect(self._on_device_changed)
        d_row.addWidget(d_label)
        d_row.addWidget(self.device_combo)
        d_row.addStretch()
        dg_layout.addLayout(d_row)

        # Refresh devices button & test tone button
        btn_row = QHBoxLayout()
        self.refresh_btn = QPushButton("↻ Refresh Device List", dev_group)
        self.refresh_btn.clicked.connect(self.populate_devices)
        btn_row.addWidget(self.refresh_btn)

        self.test_btn = QPushButton("▶ Play Test Sound", dev_group)
        self.test_btn.setObjectName("PrimaryButton")
        self.test_btn.clicked.connect(self.test_sound_requested.emit)
        btn_row.addWidget(self.test_btn)
        btn_row.addStretch()
        dg_layout.addLayout(btn_row)

        layout.addWidget(dev_group)

        # 2. Buffer Size & Latency Group
        buf_group = QGroupBox("Hardware Audio Buffer Size", self)
        bg_layout = QVBoxLayout(buf_group)
        bg_layout.setSpacing(12)

        b_row = QHBoxLayout()
        b_label = QLabel("Buffer Size (Frames):", buf_group)
        b_label.setFixedWidth(140)
        self.buffer_combo = QComboBox(buf_group)
        self.buffer_combo.setMinimumWidth(320)
        self.buffer_combo.addItem("64 frames (1.33 ms @ 48kHz — Ultra-Low)", 64)
        self.buffer_combo.addItem("128 frames (2.67 ms @ 48kHz — Recommended)", 128)
        self.buffer_combo.addItem("256 frames (5.33 ms @ 48kHz — Relaxed)", 256)
        self.buffer_combo.addItem("512 frames (10.67 ms @ 48kHz — High Headroom)", 512)
        self.buffer_combo.setCurrentIndex(1)  # 128 frames default
        self.buffer_combo.currentIndexChanged.connect(self._on_buffer_changed)
        b_row.addWidget(b_label)
        b_row.addWidget(self.buffer_combo)
        b_row.addStretch()
        bg_layout.addLayout(b_row)

        # Info Box about Latency & Bluetooth
        info_frame = QFrame(buf_group)
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #1a1e27;
                border: 1px solid #283142;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        if_layout = QVBoxLayout(info_frame)
        info_title = QLabel("💡 Low Latency Audio Information", info_frame)
        info_title.setStyleSheet("font-weight: 700; color: #38bdf8;")
        if_layout.addWidget(info_title)

        info_text = QLabel(
            "• Built-in Speakers and Wired Headphones provide instantaneous sub-3ms hardware output.\n"
            "• Bluetooth headphones (AirPods, etc.) use wireless A2DP codecs (AAC/SBC) with inherent 40-150ms "
            "hardware buffering in macOS that cannot be eliminated at the application level.\n"
            "• For the lowest physical acoustic response, use built-in speakers or 3.5mm wired audio.",
            info_frame
        )
        info_text.setWordWrap(True)
        info_text.setStyleSheet("color: #94a3b8; font-size: 12px; line-height: 1.4;")
        if_layout.addWidget(info_text)

        bg_layout.addWidget(info_frame)
        layout.addWidget(buf_group)

        layout.addStretch()
        self.populate_devices()

    def populate_devices(self):
        devices = AudioDeviceManager.get_output_devices()
        self.device_combo.blockSignals(True)
        self.device_combo.clear()

        default_idx = 0
        for idx, dev in enumerate(devices):
            label = f"{dev['name']} ({dev['channels']} ch, {dev['default_samplerate']}Hz)"
            if dev['is_default']:
                label += " [System Default]"
                default_idx = idx
            self.device_combo.addItem(label, dev['index'])

        self.device_combo.setCurrentIndex(default_idx)
        self.device_combo.blockSignals(False)

    def set_current_device_index(self, dev_index: Optional[int]):
        if dev_index is None:
            return
        for i in range(self.device_combo.count()):
            if self.device_combo.itemData(i) == dev_index:
                self.device_combo.blockSignals(True)
                self.device_combo.setCurrentIndex(i)
                self.device_combo.blockSignals(False)
                break

    def set_current_buffer_size(self, block_size: int):
        for i in range(self.buffer_combo.count()):
            if self.buffer_combo.itemData(i) == block_size:
                self.buffer_combo.blockSignals(True)
                self.buffer_combo.setCurrentIndex(i)
                self.buffer_combo.blockSignals(False)
                break

    def _on_device_changed(self, index: int):
        dev_idx = self.device_combo.currentData()
        if dev_idx is not None:
            self.device_selected.emit(dev_idx)

    def _on_buffer_changed(self, index: int):
        buf_size = self.buffer_combo.currentData()
        if buf_size is not None:
            self.buffer_size_selected.emit(buf_size)
