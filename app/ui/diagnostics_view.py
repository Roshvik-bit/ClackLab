"""
Latency diagnostics, telemetry gauges, and typing benchmark view.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGridLayout, QGroupBox, QFrame
)
from PySide6.QtCore import Qt, Signal, QTimer
from ..models import LatencyStats
from ..audio.latency_metrics import LatencyTracker

class MetricCard(QFrame):
    """Visual card displaying a single performance telemetry metric."""

    def __init__(self, title: str, initial_val: str, unit: str = "ms", parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: #17181f;
                border: 1px solid #282c38;
                border-radius: 10px;
                padding: 8px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        t_lbl = QLabel(title, self)
        t_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 600;")
        layout.addWidget(t_lbl)

        val_row = QHBoxLayout()
        self.val_lbl = QLabel(initial_val, self)
        self.val_lbl.setStyleSheet("color: #38bdf8; font-size: 20px; font-weight: 800; font-family: Menlo, Monaco, monospace;")
        val_row.addWidget(self.val_lbl)

        u_lbl = QLabel(unit, self)
        u_lbl.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 600;")
        val_row.addWidget(u_lbl)
        val_row.addStretch()

        layout.addLayout(val_row)

    def set_value(self, val: str):
        self.val_lbl.setText(val)

class DiagnosticsView(QWidget):
    """Monitors real-time event-to-audio latency and offers automated stress benchmarking."""

    run_benchmark_requested = Signal()
    reset_requested = Signal()

    def __init__(self, latency_tracker: LatencyTracker, parent=None):
        super().__init__(parent)
        self.latency_tracker = latency_tracker
        self.init_ui()

        # Telemetry update timer (every 150ms)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_telemetry)
        self.timer.start(150)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        header = QLabel("Latency Diagnostics & Benchmarking", self)
        header.setObjectName("HeaderLabel")
        header.setStyleSheet("font-size: 20px; font-weight: 800;")
        layout.addWidget(header)

        sub = QLabel("Measures monotonic event receipt to voice scheduling delay and buffer underruns.", self)
        sub.setObjectName("SubheaderLabel")
        layout.addWidget(sub)

        # 1. Telemetry Gauges Grid
        grid_frame = QFrame(self)
        grid = QGridLayout(grid_frame)
        grid.setSpacing(10)
        grid.setContentsMargins(0, 0, 0, 0)

        self.card_median = MetricCard("Median Latency (p50)", "0.00", "ms", grid_frame)
        self.card_p95 = MetricCard("95th Percentile (p95)", "0.00", "ms", grid_frame)
        self.card_max = MetricCard("Maximum Latency", "0.00", "ms", grid_frame)
        self.card_last = MetricCard("Last Keystroke Delay", "0.00", "ms", grid_frame)

        self.card_count = MetricCard("Keystrokes Measured", "0", "events", grid_frame)
        self.card_underrun = MetricCard("Buffer Underruns", "0", "drops", grid_frame)
        self.card_voices = MetricCard("Active Voice Polyphony", "0", "voices", grid_frame)
        self.card_buffer = MetricCard("PortAudio Buffer Period", "2.67", "ms", grid_frame)

        grid.addWidget(self.card_last, 0, 0)
        grid.addWidget(self.card_median, 0, 1)
        grid.addWidget(self.card_p95, 0, 2)
        grid.addWidget(self.card_max, 0, 3)

        grid.addWidget(self.card_count, 1, 0)
        grid.addWidget(self.card_underrun, 1, 1)
        grid.addWidget(self.card_voices, 1, 2)
        grid.addWidget(self.card_buffer, 1, 3)

        layout.addWidget(grid_frame)

        # 2. Benchmark Section
        bench_group = QGroupBox("Rapid-Typing Stress Benchmark", self)
        bg_layout = QVBoxLayout(bench_group)
        bg_layout.setSpacing(10)

        bench_desc = QLabel(
            "Simulates a rapid burst of 50 mechanical keystrokes in 1 second to stress-test polyphony mixing, "
            "verify memory boundedness, and measure realistic p95 latency under rapid typing load.",
            bench_group
        )
        bench_desc.setWordWrap(True)
        bench_desc.setStyleSheet("color: #94a3b8; font-size: 12px;")
        bg_layout.addWidget(bench_desc)

        btn_row = QHBoxLayout()
        self.bench_btn = QPushButton("⚡ Run Rapid Typing Benchmark (50 keys)", bench_group)
        self.bench_btn.setObjectName("PrimaryButton")
        self.bench_btn.setFixedHeight(34)
        self.bench_btn.clicked.connect(self.run_benchmark_requested.emit)
        btn_row.addWidget(self.bench_btn)

        self.reset_btn = QPushButton("↺ Reset Metrics", bench_group)
        self.reset_btn.setFixedHeight(34)
        self.reset_btn.clicked.connect(self._on_reset_clicked)
        btn_row.addWidget(self.reset_btn)

        btn_row.addStretch()
        bg_layout.addLayout(btn_row)

        layout.addWidget(bench_group)

        # 3. Lifecycle Diagnostics Logs Section
        log_group = QGroupBox("Lifecycle & Operational Logs", self)
        lg_layout = QVBoxLayout(log_group)
        lg_layout.setSpacing(8)

        from PySide6.QtWidgets import QTextEdit, QFileDialog
        from ..system.diagnostics_logger import DiagnosticsLogger

        self.log_text = QTextEdit(log_group)
        self.log_text.setReadOnly(True)
        self.log_text.setFixedHeight(140)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #121318;
                color: #a5b4fc;
                font-family: Menlo, Monaco, monospace;
                font-size: 11px;
                border: 1px solid #282c38;
                border-radius: 6px;
                padding: 6px;
            }
        """)
        lg_layout.addWidget(self.log_text)

        log_btn_row = QHBoxLayout()
        self.refresh_logs_btn = QPushButton("🔄 Refresh Logs", log_group)
        self.refresh_logs_btn.clicked.connect(self._refresh_logs)
        log_btn_row.addWidget(self.refresh_logs_btn)

        self.export_logs_btn = QPushButton("📥 Export Logs...", log_group)
        self.export_logs_btn.clicked.connect(self._export_logs)
        log_btn_row.addWidget(self.export_logs_btn)

        self.clear_logs_btn = QPushButton("🧹 Clear Logs", log_group)
        self.clear_logs_btn.clicked.connect(self._clear_logs)
        log_btn_row.addWidget(self.clear_logs_btn)

        log_btn_row.addStretch()
        lg_layout.addLayout(log_btn_row)

        layout.addWidget(log_group)
        self._refresh_logs()

        layout.addStretch()

    def _refresh_logs(self):
        from ..system.diagnostics_logger import DiagnosticsLogger
        self.log_text.setPlainText(DiagnosticsLogger.get_recent_logs())
        # Scroll to bottom
        sb = self.log_text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _export_logs(self):
        from PySide6.QtWidgets import QFileDialog
        from ..system.diagnostics_logger import DiagnosticsLogger
        path, _ = QFileDialog.getSaveFileName(self, "Export Diagnostics Log", "clacklab_diagnostics.log", "Log Files (*.log)")
        if path:
            DiagnosticsLogger.export_logs(path)

    def _clear_logs(self):
        from ..system.diagnostics_logger import DiagnosticsLogger
        DiagnosticsLogger.clear_logs()
        self._refresh_logs()

    def refresh_telemetry(self):
        stats = self.latency_tracker.get_stats()
        self.card_median.set_value(str(stats.median_ms))
        self.card_p95.set_value(str(stats.p95_ms))
        self.card_max.set_value(str(stats.max_ms))
        self.card_last.set_value(str(stats.last_ms))
        self.card_count.set_value(str(stats.count))
        self.card_underrun.set_value(str(stats.buffer_underruns))
        self.card_voices.set_value(str(stats.active_voices))
        period_ms = round(stats.block_size / stats.sample_rate * 1000.0, 2)
        self.card_buffer.set_value(str(period_ms))

    def _on_reset_clicked(self):
        self.latency_tracker.reset()
        self.reset_requested.emit()
        self.refresh_telemetry()
