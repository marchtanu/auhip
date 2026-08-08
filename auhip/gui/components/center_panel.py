from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt
from auhip.gui.theme import COLORS
from .waveform_widget import WaveformWidget
from .vision_panel import VisionPanel
from .transcript_panel import TranscriptPanel
from .response_panel import ResponsePanel

class CenterPanel(QWidget):
    def __init__(self, vision_worker=None, parent=None):
        super().__init__(parent)
        self._vision_worker = vision_worker
        self.setStyleSheet("background: transparent; border: none;")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Audio waveform card
        self.wave_card = QFrame()
        self.wave_card.setStyleSheet(
            f"QFrame {{ background: {COLORS['panel']}; border: 1px solid {COLORS['border']};"
            "border-radius: 12px; }"
        )
        self.wave_card.setFixedHeight(80)
        wl = QVBoxLayout(self.wave_card)
        wl.setContentsMargins(14, 8, 14, 8)
        wl.setSpacing(2)

        self.wave_header = QLabel("Audio input")
        self.wave_header.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 10px; font-weight: 600;"
            "letter-spacing: 0.4px; text-transform: uppercase; border: none;"
        )
        wl.addWidget(self.wave_header)

        self.waveform = WaveformWidget()
        wl.addWidget(self.waveform, 1)
        layout.addWidget(self.wave_card)

        # Vision Panel (Hidden by default)
        self.vision_panel = VisionPanel()
        self.vision_panel.hide()
        layout.addWidget(self.vision_panel)
        
        if self._vision_worker:
            self._vision_worker.frame_ready.connect(self.vision_panel.update_frame)
            self._vision_worker.vision_data_ready.connect(self.vision_panel.update_data)
            self.vision_panel.calib_btn.clicked.connect(self._vision_worker.calibrate)

        # Transcript + Response split
        split = QWidget()
        split.setStyleSheet("background: transparent; border: none;")
        split_layout = QHBoxLayout(split)
        split_layout.setContentsMargins(0, 0, 0, 0)
        split_layout.setSpacing(10)

        # Transcript card
        self.transcript_card = QFrame()
        self.transcript_card.setStyleSheet(
            f"QFrame {{ background: {COLORS['panel']}; border: 1px solid {COLORS['border']};"
            "border-radius: 12px; }"
        )
        tl = QVBoxLayout(self.transcript_card)
        tl.setContentsMargins(14, 12, 14, 12)
        tl.setSpacing(8)
        self.t_header = QLabel("Live transcript")
        self.t_header.setStyleSheet(
            f"color: {COLORS['text']}; font-size: 14px; font-weight: 600;"
            "letter-spacing: -0.1px; border: none;"
        )
        tl.addWidget(self.t_header)
        self.transcript = TranscriptPanel()
        tl.addWidget(self.transcript, 1)
        split_layout.addWidget(self.transcript_card, 1)

        # Response card
        self.response_card = QFrame()
        self.response_card.setStyleSheet(
            f"QFrame {{ background: {COLORS['panel_soft']}; border: 1px solid {COLORS['border']};"
            "border-radius: 12px; }"
        )
        rl = QVBoxLayout(self.response_card)
        rl.setContentsMargins(14, 12, 14, 12)
        rl.setSpacing(8)
        self.r_header = QLabel("auhip response")
        self.r_header.setStyleSheet(
            f"color: {COLORS['text']}; font-size: 14px; font-weight: 600;"
            "letter-spacing: -0.1px; border: none;"
        )
        rl.addWidget(self.r_header)
        self.response = ResponsePanel()
        rl.addWidget(self.response, 1)
        split_layout.addWidget(self.response_card, 1)

        layout.addWidget(split, 1)


    def refresh_theme(self, dark: bool = False):
        """Re-apply styles after a theme switch."""
        self.wave_card.setStyleSheet(
            f"QFrame {{ background: {COLORS['panel']}; border: 1px solid {COLORS['border']};"
            "border-radius: 12px; }"
        )
        self.wave_header.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 11px; font-weight: 500;"
            "letter-spacing: 0.3px; text-transform: uppercase; border: none;"
        )
        self.transcript_card.setStyleSheet(
            f"QFrame {{ background: {COLORS['panel']}; border: 1px solid {COLORS['border']};"
            "border-radius: 12px; }"
        )
        self.t_header.setStyleSheet(
            f"color: {COLORS['text']}; font-size: 15px; font-weight: 600;"
            "letter-spacing: -0.1px; border: none;"
        )
        self.response_card.setStyleSheet(
            f"QFrame {{ background: {COLORS['panel_soft']}; border: 1px solid {COLORS['border']};"
            "border-radius: 12px; }"
        )
        self.r_header.setStyleSheet(
            f"color: {COLORS['text']}; font-size: 15px; font-weight: 600;"
            "letter-spacing: -0.1px; border: none;"
        )
        
        self.waveform.update()
        self.vision_panel.refresh_theme()
        self.transcript.refresh_theme()
        self.response.refresh_theme()

