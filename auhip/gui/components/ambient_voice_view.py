import time
import math
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QScrollArea,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter,
    QColor,
    QFont,
    QRadialGradient,
    QLinearGradient,
)

from .ambient_orb_widget import AmbientOrbWidget


class PulsingDots(QWidget):
    """Three circular animated dots: ● ● ● (first slightly darker, others progressively softer)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(54, 18)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(24)
        self._start_time = time.time()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        t = time.time() - self._start_time

        dot_r = 3.5
        spacing = 14.0
        start_x = 13.0
        cy = 9.0

        for i in range(3):
            # Harmonic phase shift between dots
            wave = (math.sin(t * 3.6 - i * 0.75) + 1.0) / 2.0
            base_alpha = 240 - (i * 55)
            alpha = int(max(70, min(255, base_alpha * (0.65 + wave * 0.35))))
            r = dot_r + wave * 0.8

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(67, 56, 202, alpha))
            painter.drawEllipse(QPointF(start_x + i * spacing, cy), r, r)

        painter.end()


class PulsingIndicator(QWidget):
    """Subtle pulsing glowing dot indicator accompanying the live transcript."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(14, 14)
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self.update)
        self._pulse_timer.start(24)
        self._start_time = time.time()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        t = time.time() - self._start_time
        pulse = (1.0 + math.sin(t * 4.0)) / 2.0

        r = 3.0 + pulse * 2.0
        alpha = int(90 + pulse * 140)

        halo_grad = QRadialGradient(QPointF(7, 7), r * 1.6)
        halo_grad.setColorAt(0.0, QColor(99, 102, 241, alpha))
        halo_grad.setColorAt(1.0, QColor(99, 102, 241, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(halo_grad)
        painter.drawEllipse(QPointF(7, 7), r * 1.6, r * 1.6)

        painter.setBrush(QColor(99, 102, 241, 230))
        painter.drawEllipse(QPointF(7, 7), 2.2, 2.2)
        painter.end()


class AmbientVoiceView(QWidget):
    """
    High-Fidelity Desktop AI Voice Assistant Interface for AUHIP:
    - Soft atmospheric lavender, periwinkle, pale blue, and white gradient with subtle vignette
    - Floating frosted-glass top navigation bar (~75% screen width) with status pill and clock
    - Centered STATUS area: small uppercase label, large 'Listening' typography, and 3 pulsing dots
    - Central AI Orb (380-450px) with flowing liquid plasma/clouds and horizontal audio waveform
    - Centered live speech transcription with animated glowing pulsing indicator
    """

    toggle_mode_requested = pyqtSignal()
    push_to_talk_pressed = pyqtSignal()
    push_to_talk_released = pyqtSignal()
    cancel_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_cmd_text = "Search for MCP documentation"
        self._full_transcript = "Can you analyze the performance of the AUHIP background system?"
        self._is_user_transcript = True
        self._build_ui()

    def paintEvent(self, event):
        """
        Paints the atmospheric background:
        - Darker periwinkle/lavender around outer edges (subtle vignette)
        - Brighter white-blue glow concentrated around center
        - Soft luminous atmosphere
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = h / 2.0

        # Outer periwinkle/lavender gradient
        outer_grad = QLinearGradient(0, 0, w, h)
        outer_grad.setColorAt(0.0, QColor(219, 215, 249))  # Lavender corner
        outer_grad.setColorAt(0.35, QColor(230, 232, 255)) # Soft periwinkle
        outer_grad.setColorAt(0.70, QColor(222, 226, 252)) # Pale blue-violet
        outer_grad.setColorAt(1.0, QColor(209, 213, 248))  # Darker periwinkle corner
        painter.fillRect(self.rect(), outer_grad)

        # Concentrated bright white-blue center illumination bloom
        radial_r = max(w, h) * 0.55
        center_glow = QRadialGradient(QPointF(cx, cy), radial_r)
        center_glow.setColorAt(0.0, QColor(255, 255, 255, 210))
        center_glow.setColorAt(0.32, QColor(245, 243, 255, 140))
        center_glow.setColorAt(0.65, QColor(230, 235, 255, 60))
        center_glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillRect(self.rect(), center_glow)

        painter.end()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 28)
        main_layout.setSpacing(6)

        # ── 1. Floating Top Navigation Bar (~75% screen width) ────────────────
        top_container = QHBoxLayout()
        top_container.addStretch(1)

        self.nav_pill = QFrame()
        self.nav_pill.setFixedHeight(50)
        self.nav_pill.setMinimumWidth(740)
        self.nav_pill.setMaximumWidth(980)
        self.nav_pill.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.72);
                border: 1px solid rgba(255, 255, 255, 0.90);
                border-radius: 25px;
            }
        """)

        np_layout = QHBoxLayout(self.nav_pill)
        np_layout.setContentsMargins(16, 0, 16, 0)
        np_layout.setSpacing(10)

        # LEFT: Star icon + auhip + v2.4 OS
        star_lbl = QLabel("✦")
        star_lbl.setFont(QFont("Segoe UI Symbol", 12))
        star_lbl.setStyleSheet("color: #1E1B4B; border: none; background: transparent;")
        np_layout.addWidget(star_lbl)

        brand_lbl = QLabel("auhip")
        brand_lbl.setFont(QFont("Inter", 13, QFont.Weight.DemiBold))
        brand_lbl.setStyleSheet("color: #1E1B4B; border: none; background: transparent; letter-spacing: -0.3px;")
        np_layout.addWidget(brand_lbl)

        v_pill = QLabel("v2.4 OS")
        v_pill.setFont(QFont("Inter", 9, QFont.Weight.Medium))
        v_pill.setStyleSheet("""
            color: #64748B;
            background: rgba(241, 245, 249, 0.90);
            border: 1px solid rgba(226, 232, 240, 0.8);
            border-radius: 9px;
            padding: 2px 7px;
        """)
        np_layout.addWidget(v_pill)

        np_layout.addSpacing(6)

        # CENTER-LEFT: Last Command Pill with glowing purple status dot
        last_cmd_pill = QFrame()
        last_cmd_pill.setFixedHeight(30)
        last_cmd_pill.setStyleSheet("""
            QFrame {
                background: rgba(245, 243, 255, 0.90);
                border: 1px solid rgba(221, 214, 254, 0.7);
                border-radius: 15px;
            }
        """)
        lc_layout = QHBoxLayout(last_cmd_pill)
        lc_layout.setContentsMargins(10, 0, 12, 0)
        lc_layout.setSpacing(6)

        purple_dot = QLabel("●")
        purple_dot.setFont(QFont("Inter", 8, QFont.Weight.Bold))
        purple_dot.setStyleSheet("color: #7C3AED; border: none; background: transparent;")
        lc_layout.addWidget(purple_dot)

        self.last_cmd_lbl = QLabel(f"Last Command: {self._last_cmd_text}")
        self.last_cmd_lbl.setFont(QFont("Inter", 10, QFont.Weight.Medium))
        self.last_cmd_lbl.setStyleSheet("color: #4338CA; border: none; background: transparent;")
        lc_layout.addWidget(self.last_cmd_lbl)
        np_layout.addWidget(last_cmd_pill)

        np_layout.addStretch(1)

        # RIGHT: 12:45 + Ready + Sun + Cockpit + Settings
        self.clock_lbl = QLabel("12:45")
        self.clock_lbl.setFont(QFont("Inter", 11, QFont.Weight.Medium))
        self.clock_lbl.setStyleSheet("color: #475569; border: none; background: transparent;")
        self._update_clock()
        np_layout.addWidget(self.clock_lbl)

        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)

        status_dot = QLabel("● Ready")
        status_dot.setFont(QFont("Inter", 10, QFont.Weight.DemiBold))
        status_dot.setStyleSheet("color: #16A34A; border: none; background: transparent;")
        np_layout.addWidget(status_dot)

        # Sun icon button
        sun_btn = QPushButton("☼")
        sun_btn.setFixedSize(28, 28)
        sun_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        sun_btn.setFont(QFont("Segoe UI Symbol", 13))
        sun_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #64748B;
                border: none;
                border-radius: 14px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.9);
                color: #1E1B4B;
            }
        """)
        np_layout.addWidget(sun_btn)

        # Cockpit mode toggle button
        self.cockpit_btn = QPushButton("🎛️ Cockpit")
        self.cockpit_btn.setFixedHeight(28)
        self.cockpit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cockpit_btn.setFont(QFont("Inter", 10, QFont.Weight.DemiBold))
        self.cockpit_btn.setStyleSheet("""
            QPushButton {
                background: #0C0A09;
                color: #FFFFFF;
                border: none;
                border-radius: 14px;
                padding: 0 12px;
            }
            QPushButton:hover {
                background: #1E1B4B;
            }
        """)
        self.cockpit_btn.clicked.connect(self.toggle_mode_requested.emit)
        np_layout.addWidget(self.cockpit_btn)

        # Settings gear button
        gear_btn = QPushButton("⚙")
        gear_btn.setFixedSize(28, 28)
        gear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        gear_btn.setFont(QFont("Segoe UI Symbol", 12))
        gear_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #64748B;
                border: none;
                border-radius: 14px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.9);
                color: #1E1B4B;
            }
        """)
        np_layout.addWidget(gear_btn)

        top_container.addWidget(self.nav_pill)
        top_container.addStretch(1)
        main_layout.addLayout(top_container)

        main_layout.addSpacing(6)

        # ── 2. Status Area (Centered Below Floating Navbar) ───────────────────
        status_box = QVBoxLayout()
        status_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_box.setSpacing(2)

        self.status_sub = QLabel("STATUS")
        self.status_sub.setFont(QFont("Inter", 9, QFont.Weight.Bold))
        self.status_sub.setStyleSheet("color: #6366F1; letter-spacing: 2.5px; border: none; background: transparent;")
        status_box.addWidget(self.status_sub, alignment=Qt.AlignmentFlag.AlignCenter)

        self.status_main = QLabel("Listening")
        self.status_main.setFont(QFont("Inter", 36, QFont.Weight.Medium))
        self.status_main.setStyleSheet("color: #1E1B4B; border: none; background: transparent; letter-spacing: -0.5px;")
        self.status_pill = self.status_main  # Backwards compatibility alias
        status_box.addWidget(self.status_main, alignment=Qt.AlignmentFlag.AlignCenter)

        self.pulsing_dots = PulsingDots()
        status_box.addWidget(self.pulsing_dots, alignment=Qt.AlignmentFlag.AlignCenter)

        main_layout.addLayout(status_box)

        # ── 3. Central AI Orb & Continuous Horizontal Audio Waveform ──────────
        self.orb_widget = AmbientOrbWidget(self)
        main_layout.addWidget(self.orb_widget, 1)

        # ── 4. Bottom Live Speech Transcription Box ───────────────────────────
        bottom_container = QHBoxLayout()
        bottom_container.addStretch(1)

        self.hearing_box = QFrame()
        self.hearing_box.setObjectName("hearing_box")
        self.hearing_box.setMinimumHeight(140)
        self.hearing_box.setMaximumHeight(260)
        self.hearing_box.setMinimumWidth(820)
        self.hearing_box.setMaximumWidth(1040)
        self.hearing_box.setStyleSheet("""
            QFrame#hearing_box {
                background: rgba(255, 255, 255, 0.90);
                border: 1.5px solid rgba(255, 255, 255, 0.98);
                border-radius: 24px;
            }
        """)

        # Soft luminous drop shadow for floating capsule depth
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect(self.hearing_box)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(99, 102, 241, 45))
        shadow.setOffset(0, 4)
        self.hearing_box.setGraphicsEffect(shadow)

        box_layout = QVBoxLayout(self.hearing_box)
        box_layout.setContentsMargins(36, 16, 36, 18)
        box_layout.setSpacing(8)
        box_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Header tag row with animated glowing live indicator dot
        tag_row = QHBoxLayout()
        tag_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tag_row.setSpacing(8)

        self.indicator = PulsingIndicator()
        tag_row.addWidget(self.indicator)

        self.hearing_tag = QLabel("WHAT AUHIP IS HEARING")
        self.hearing_tag.setFont(QFont("Inter", 10, QFont.Weight.Bold))
        self.hearing_tag.setStyleSheet("color: #4F46E5; letter-spacing: 2.2px; border: none; background: transparent;")
        tag_row.addWidget(self.hearing_tag)

        box_layout.addLayout(tag_row)

        # Smooth borderless scroll container so multi-line text never gets cut off
        self.transcript_scroll = QScrollArea()
        self.transcript_scroll.setWidgetResizable(True)
        self.transcript_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.transcript_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.transcript_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                width: 5px;
                background: transparent;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(99, 102, 241, 0.35);
                border-radius: 2px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self.heard_lbl = QLabel(f'“{self._full_transcript}”')
        self.heard_lbl.setFont(QFont("Inter", 18, QFont.Weight.Medium))
        self.heard_lbl.setStyleSheet("""
            QLabel {
                color: #0F172A;
                border: none;
                background: transparent;
                padding: 2px 14px;
            }
        """)
        self.heard_lbl.setWordWrap(True)
        self.heard_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.transcript_scroll.setWidget(self.heard_lbl)

        box_layout.addWidget(self.transcript_scroll)

        bottom_container.addWidget(self.hearing_box)
        bottom_container.addStretch(1)

        main_layout.addLayout(bottom_container)
        main_layout.addSpacing(16)

    def _update_clock(self):
        now = datetime.now().strftime("%H:%M")
        self.clock_lbl.setText(now)

    def set_status(self, state: str, label: str = ""):
        s = state.upper()
        if "VOICE" in s or "LISTEN" in s:
            self.status_main.setText("Listening")
            self.status_sub.setText("STATUS")
            if self._is_user_transcript:
                self.hearing_tag.setText("WHAT AUHIP IS HEARING")
                self.hearing_tag.setStyleSheet("color: #4F46E5; letter-spacing: 2.2px; border: none; background: transparent;")
        elif "PROCESS" in s or "THINK" in s:
            self.status_main.setText("Thinking")
            self.status_sub.setText("STATUS")
            self.hearing_tag.setText("PROCESSING")
            self.hearing_tag.setStyleSheet("color: #6366F1; letter-spacing: 2.2px; border: none; background: transparent;")
        elif "SPEAK" in s:
            self.status_main.setText("Speaking")
            self.status_sub.setText("STATUS")
            self.hearing_tag.setText("AUHIP RESPONSE")
            self.hearing_tag.setStyleSheet("color: #7C3AED; letter-spacing: 2.2px; border: none; background: transparent;")
        else:
            self.status_main.setText("Ready")
            self.status_sub.setText("STATUS")
            if self._is_user_transcript:
                self.hearing_tag.setText("READY")
                self.hearing_tag.setStyleSheet("color: #64748B; letter-spacing: 2.2px; border: none; background: transparent;")

        self.orb_widget.set_status_label(self.status_main.text())

    def set_speaking(self, is_speaking: bool):
        self.orb_widget.set_speaking_state(is_speaking)
        if is_speaking:
            self.set_status("SPEAKING")
        else:
            self.set_status("VOICE_MODE")

    def show_transcript(self, text: str, is_user: bool = True):
        self._full_transcript = text
        self._is_user_transcript = is_user
        self.heard_lbl.setText(f'“{text}”')
        if is_user:
            self.hearing_tag.setText("WHAT AUHIP IS HEARING")
            self.hearing_tag.setStyleSheet("color: #4F46E5; letter-spacing: 2.2px; border: none; background: transparent;")
        else:
            self.hearing_tag.setText("AUHIP RESPONSE")
            self.hearing_tag.setStyleSheet("color: #7C3AED; letter-spacing: 2.2px; border: none; background: transparent;")

    def set_last_command(self, cmd: str):
        self._last_cmd_text = cmd
        self.last_cmd_lbl.setText(f"Last Command: {cmd}")

    def feed_audio(self, chunk):
        self.orb_widget.update_audio(chunk)
