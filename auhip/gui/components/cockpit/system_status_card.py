import psutil
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QProgressBar,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from auhip.gui.theme import COLORS
from auhip.gui.components.ambient_orb_widget import AmbientOrbWidget


class SystemStatusCard(QFrame):
    """
    Left-column System Status Card matching the reference design in white editorial print aesthetic:
    - FSM State, Microphone, and Voice Output status indicators
    - Double-snap acoustic detector circles
    - CPU, RAM, and GPU hardware gauges with activity indicators
    - Embedded mini gaseous ambient orb visualizer
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(240)
        self._build_ui()

        # Update metrics every 2.5 seconds
        self._metrics_timer = QTimer(self)
        self._metrics_timer.timeout.connect(self._update_metrics)
        self._metrics_timer.start(2500)
        self._update_metrics()

    def _build_ui(self):
        self.setStyleSheet(f"""
            SystemStatusCard {{
                background: #FFFFFF;
                border: 1px solid #E7E5E4;
                border-radius: 16px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 14)
        layout.setSpacing(10)

        # ── Header ────────────────────────────────────────────────────────────
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        self.title_lbl = QLabel("SYSTEM STATUS")
        self.title_lbl.setFont(QFont("Inter", 10, QFont.Weight.Bold))
        self.title_lbl.setStyleSheet("color: #777169; letter-spacing: 0.8px; border: none; background: transparent;")
        header_row.addWidget(self.title_lbl)
        header_row.addStretch()

        self.chevron_lbl = QLabel("‹")
        self.chevron_lbl.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        self.chevron_lbl.setStyleSheet("color: #A8A29E; border: none; background: transparent;")
        header_row.addWidget(self.chevron_lbl)
        layout.addLayout(header_row)

        layout.addSpacing(2)

        # ── State Indicator ───────────────────────────────────────────────────
        layout.addWidget(self._make_section_label("STATE"))
        state_row = QHBoxLayout()
        state_row.setSpacing(8)
        self.state_dot = QLabel("●")
        self.state_dot.setStyleSheet("color: #16A34A; font-size: 11px; border: none; background: transparent;")
        state_row.addWidget(self.state_dot)

        self.state_lbl = QLabel("Ready")
        self.state_lbl.setFont(QFont("Inter", 13, QFont.Weight.DemiBold))
        self.state_lbl.setStyleSheet("color: #0C0A09; border: none; background: transparent;")
        state_row.addWidget(self.state_lbl)
        state_row.addStretch()
        layout.addLayout(state_row)

        # ── Microphone Status ─────────────────────────────────────────────────
        layout.addWidget(self._make_section_label("MICROPHONE"))
        mic_row = QHBoxLayout()
        mic_row.setSpacing(8)
        self.mic_dot = QLabel("●")
        self.mic_dot.setStyleSheet("color: #16A34A; font-size: 10px; border: none; background: transparent;")
        mic_row.addWidget(self.mic_dot)

        self.mic_lbl = QLabel("Listening...")
        self.mic_lbl.setFont(QFont("Inter", 12, QFont.Weight.Medium))
        self.mic_lbl.setStyleSheet("color: #4E4E4E; border: none; background: transparent;")
        mic_row.addWidget(self.mic_lbl)
        mic_row.addStretch()
        layout.addLayout(mic_row)

        # ── Voice Output Status ───────────────────────────────────────────────
        layout.addWidget(self._make_section_label("VOICE OUTPUT (TTS)"))
        tts_row = QHBoxLayout()
        tts_row.setSpacing(8)
        self.tts_dot = QLabel("●")
        self.tts_dot.setStyleSheet("color: #16A34A; font-size: 10px; border: none; background: transparent;")
        tts_row.addWidget(self.tts_dot)

        self.tts_lbl = QLabel("Speaking ready")
        self.tts_lbl.setFont(QFont("Inter", 12, QFont.Weight.Medium))
        self.tts_lbl.setStyleSheet("color: #4E4E4E; border: none; background: transparent;")
        tts_row.addWidget(self.tts_lbl)
        tts_row.addStretch()
        layout.addLayout(tts_row)

        # ── Snap Detector ─────────────────────────────────────────────────────
        layout.addWidget(self._make_section_label("SNAP DETECTOR"))
        snap_row = QHBoxLayout()
        snap_row.setSpacing(8)
        self.snap_dot1 = QLabel("○")
        self.snap_dot1.setStyleSheet("color: #C8B8E0; font-size: 16px; border: none; background: transparent;")
        self.snap_dot2 = QLabel("○")
        self.snap_dot2.setStyleSheet("color: #E7E5E4; font-size: 16px; border: none; background: transparent;")
        snap_row.addWidget(self.snap_dot1)
        snap_row.addWidget(self.snap_dot2)

        self.snap_status_lbl = QLabel("Listening for snaps")
        self.snap_status_lbl.setFont(QFont("Inter", 11))
        self.snap_status_lbl.setStyleSheet("color: #777169; border: none; background: transparent;")
        snap_row.addWidget(self.snap_status_lbl)
        snap_row.addStretch()
        layout.addLayout(snap_row)

        layout.addSpacing(4)
        layout.addWidget(self._make_divider())
        layout.addSpacing(4)

        # ── Hardware Activity Gauges ──────────────────────────────────────────
        self.cpu_bar, self.cpu_val = self._create_gauge_row(layout, "CPU", "#292524")
        self.ram_bar, self.ram_val = self._create_gauge_row(layout, "RAM", "#7E22CE")
        self.gpu_bar, self.gpu_val = self._create_gauge_row(layout, "GPU", "#2563EB")

        layout.addStretch(1)

        # ── Embedded Mini Ambient Gas Orb ─────────────────────────────────────
        self.mini_orb = AmbientOrbWidget()
        self.mini_orb.setFixedHeight(120)
        self.mini_orb.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self.mini_orb)

    def _make_section_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(QFont("Inter", 9, QFont.Weight.DemiBold))
        lbl.setStyleSheet("color: #A8A29E; letter-spacing: 0.6px; border: none; background: transparent; margin-top: 4px;")
        return lbl

    def _make_divider(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background: #F0EFED; border: none; max-height: 1px;")
        return line

    def _create_gauge_row(self, parent_layout, label_text: str, fill_color: str):
        row = QHBoxLayout()
        row.setSpacing(8)

        lbl = QLabel(label_text)
        lbl.setFixedWidth(32)
        lbl.setFont(QFont("Inter", 11, QFont.Weight.DemiBold))
        lbl.setStyleSheet("color: #4E4E4E; border: none; background: transparent;")
        row.addWidget(lbl)

        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setTextVisible(False)
        bar.setFixedHeight(5)
        bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #F0EFED;
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {fill_color};
                border-radius: 2px;
            }}
        """)
        row.addWidget(bar, 1)

        sparkle = QLabel("∿")
        sparkle.setStyleSheet("color: #A8A29E; font-size: 11px; border: none; background: transparent;")
        row.addWidget(sparkle)

        val_lbl = QLabel("0%")
        val_lbl.setFixedWidth(32)
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        val_lbl.setFont(QFont("Inter", 11, QFont.Weight.Medium))
        val_lbl.setStyleSheet("color: #0C0A09; border: none; background: transparent;")
        row.addWidget(val_lbl)

        parent_layout.addLayout(row)
        return bar, val_lbl

    def _update_metrics(self):
        try:
            cpu = int(psutil.cpu_percent())
            ram = int(psutil.virtual_memory().percent)
            # Estimate GPU or default
            gpu = 28
            try:
                import pynvml
                pynvml.nvmlInit()
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                gpu = int(util.gpu)
            except Exception:
                gpu = max(10, min(85, int(cpu * 1.2)))

            self.cpu_bar.setValue(cpu)
            self.cpu_val.setText(f"{cpu}%")

            self.ram_bar.setValue(ram)
            self.ram_val.setText(f"{ram}%")

            self.gpu_bar.setValue(gpu)
            self.gpu_val.setText(f"{gpu}%")
        except Exception:
            pass

    def set_state(self, state_name: str, label: str = ""):
        clean = label if label else state_name.capitalize()
        self.state_lbl.setText(clean)
        self.mini_orb.set_status_label(state_name)

        if "VOICE" in state_name or "LISTENING" in state_name:
            self.state_dot.setStyleSheet("color: #2563EB; font-size: 11px; background: transparent;")
            self.mic_lbl.setText("Listening...")
            self.mic_dot.setStyleSheet("color: #2563EB; font-size: 10px; background: transparent;")
        elif "PROCESS" in state_name or "THINKING" in state_name:
            self.state_dot.setStyleSheet("color: #7E22CE; font-size: 11px; background: transparent;")
            self.mic_lbl.setText("Processing...")
        elif "SPEAK" in state_name:
            self.state_dot.setStyleSheet("color: #16A34A; font-size: 11px; background: transparent;")
            self.tts_lbl.setText("Speaking...")
            self.tts_dot.setStyleSheet("color: #16A34A; font-size: 10px; background: transparent;")
        else:
            self.state_dot.setStyleSheet("color: #16A34A; font-size: 11px; background: transparent;")
            self.mic_lbl.setText("Mic ready")
            self.tts_lbl.setText("Speaking ready")

    def set_tts_active(self, active: bool, speaking: bool = False):
        self.mini_orb.set_speaking_state(speaking)
        if speaking:
            self.tts_lbl.setText("Speaking...")
            self.tts_dot.setStyleSheet("color: #16A34A; font-size: 10px; background: transparent;")
        else:
            self.tts_lbl.setText("Speaking ready" if active else "Muted")
            self.tts_dot.setStyleSheet("color: #16A34A; font-size: 10px; background: transparent;" if active else "color: #A8A29E; font-size: 10px; background: transparent;")

    def update_snaps(self, count: int):
        if count == 1:
            self.snap_dot1.setText("●")
            self.snap_dot1.setStyleSheet("color: #7E22CE; font-size: 16px; border: none; background: transparent;")
            self.snap_dot2.setText("○")
            self.snap_dot2.setStyleSheet("color: #E7E5E4; font-size: 16px; border: none; background: transparent;")
            self.snap_status_lbl.setText("Snap 1 detected")
        elif count >= 2:
            self.snap_dot1.setText("●")
            self.snap_dot1.setStyleSheet("color: #16A34A; font-size: 16px; border: none; background: transparent;")
            self.snap_dot2.setText("●")
            self.snap_dot2.setStyleSheet("color: #16A34A; font-size: 16px; border: none; background: transparent;")
            self.snap_status_lbl.setText("Snap 2 triggered!")
        else:
            self.snap_dot1.setText("○")
            self.snap_dot1.setStyleSheet("color: #C8B8E0; font-size: 16px; border: none; background: transparent;")
            self.snap_dot2.setText("○")
            self.snap_dot2.setStyleSheet("color: #E7E5E4; font-size: 16px; border: none; background: transparent;")
            self.snap_status_lbl.setText("Listening for snaps")

    def feed_audio(self, chunk):
        self.mini_orb.update_audio(chunk)
