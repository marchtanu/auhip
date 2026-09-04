import cv2
import numpy as np
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QImage, QPixmap

from auhip.core.event_bus import event_bus


class VisionControlHUD(QFrame):
    """
    Dedicated Vision & Air-Mouse Control HUD matching docs/DESIGN.md:
    - Live OpenCV video canvas with MediaPipe facial/hand tracking overlays
    - Camera Mode: Gaze vector, blink detection, attention state, FPS, center gaze calibration
    - Control Mode: Air-mouse cursor position, pinch click indicator, hand gesture classification
    - On/Off camera power gating toggle and mode switcher
    """

    close_requested = pyqtSignal()
    calibrate_requested = pyqtSignal()
    exit_control_requested = pyqtSignal()
    start_camera_requested = pyqtSignal()
    stop_camera_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_control_mode = False
        self._is_camera_active = False
        self.setStyleSheet("""
            VisionControlHUD {
                background: #FFFFFF;
                border: 1px solid #E7E5E4;
                border-radius: 16px;
            }
        """)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # ── 1. Header Row ─────────────────────────────────────────────────────
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(10)

        self.title_lbl = QLabel("👁️ Vision & Attention HUD")
        self.title_lbl.setFont(QFont("Inter", 12, QFont.Weight.DemiBold))
        self.title_lbl.setStyleSheet("color: #0C0A09; border: none; background: transparent;")
        header_row.addWidget(self.title_lbl)

        # Active Mode Pill Badge
        self.mode_badge = QLabel("● Vision Active")
        self.mode_badge.setFont(QFont("Inter", 9, QFont.Weight.Bold))
        self.mode_badge.setStyleSheet("""
            color: #7E22CE;
            background: #F5F3FF;
            border: 1px solid #DDD6FE;
            border-radius: 10px;
            padding: 2px 8px;
        """)
        header_row.addWidget(self.mode_badge)

        header_row.addStretch(1)

        # FPS Pill
        self.fps_lbl = QLabel("FPS: 0")
        self.fps_lbl.setFont(QFont("Inter", 9, QFont.Weight.Medium))
        self.fps_lbl.setStyleSheet("""
            color: #777169;
            background: #F0EFED;
            border-radius: 8px;
            padding: 2px 6px;
            border: none;
        """)
        header_row.addWidget(self.fps_lbl)

        # Camera Power Toggle Button
        self.cam_toggle_btn = QPushButton("📹 Turn Off Camera")
        self.cam_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cam_toggle_btn.setFont(QFont("Inter", 10, QFont.Weight.Medium))
        self.cam_toggle_btn.setStyleSheet("""
            QPushButton {
                background: #F0EFED;
                color: #292524;
                border: 1px solid #E7E5E4;
                border-radius: 8px;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background: #E7E5E4;
            }
        """)
        self.cam_toggle_btn.clicked.connect(self._toggle_camera_power)
        header_row.addWidget(self.cam_toggle_btn)

        # Close button
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #777169;
                border: none;
                border-radius: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #FEE2E2;
                color: #DC2626;
            }
        """)
        self.close_btn.clicked.connect(self.close_requested.emit)
        header_row.addWidget(self.close_btn)

        layout.addLayout(header_row)

        # ── 2. Live Camera Viewport ───────────────────────────────────────────
        self.feed_container = QFrame()
        self.feed_container.setMinimumHeight(280)
        self.feed_container.setStyleSheet("""
            QFrame {
                background: #1C1917;
                border-radius: 12px;
                border: 1px solid #292524;
            }
        """)
        feed_layout = QVBoxLayout(self.feed_container)
        feed_layout.setContentsMargins(0, 0, 0, 0)

        self.feed_lbl = QLabel("Camera Feed Offline\n(Waiting for Vision or Control Mode)")
        self.feed_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.feed_lbl.setFont(QFont("Inter", 12))
        self.feed_lbl.setStyleSheet("color: #A8A29E; border: none; background: transparent;")
        feed_layout.addWidget(self.feed_lbl, 1)

        layout.addWidget(self.feed_container, 1)

        # ── 3. Real-Time Telemetry Bar ────────────────────────────────────────
        telemetry_card = QFrame()
        telemetry_card.setStyleSheet("""
            QFrame {
                background: #FAFAFA;
                border: 1px solid #E7E5E4;
                border-radius: 10px;
                padding: 4px 8px;
            }
        """)
        t_layout = QHBoxLayout(telemetry_card)
        t_layout.setContentsMargins(10, 6, 10, 6)
        t_layout.setSpacing(14)

        # Telemetry columns: Gaze, Blink, Attention, Hand / Gesture
        self.gaze_lbl = QLabel("Gaze: Center")
        self.gaze_lbl.setFont(QFont("Inter", 11, QFont.Weight.Medium))
        self.gaze_lbl.setStyleSheet("color: #0C0A09; border: none; background: transparent;")
        t_layout.addWidget(self.gaze_lbl)

        self.blink_lbl = QLabel("Blink: Both Open")
        self.blink_lbl.setFont(QFont("Inter", 11))
        self.blink_lbl.setStyleSheet("color: #777169; border: none; background: transparent;")
        t_layout.addWidget(self.blink_lbl)

        self.attention_lbl = QLabel("Attention: Focused")
        self.attention_lbl.setFont(QFont("Inter", 11, QFont.Weight.Medium))
        self.attention_lbl.setStyleSheet("color: #16A34A; border: none; background: transparent;")
        t_layout.addWidget(self.attention_lbl)

        self.hand_lbl = QLabel("Gesture: Ready")
        self.hand_lbl.setFont(QFont("Inter", 11, QFont.Weight.DemiBold))
        self.hand_lbl.setStyleSheet("color: #2563EB; border: none; background: transparent;")
        t_layout.addWidget(self.hand_lbl, 1)

        layout.addWidget(telemetry_card)

        # ── 4. Control Action Bar ─────────────────────────────────────────────
        actions_row = QHBoxLayout()
        actions_row.setContentsMargins(0, 0, 0, 0)
        actions_row.setSpacing(8)

        self.calib_btn = QPushButton("🎯 Calibrate Center Gaze")
        self.calib_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.calib_btn.setFont(QFont("Inter", 10, QFont.Weight.DemiBold))
        self.calib_btn.setStyleSheet("""
            QPushButton {
                background: #FFFFFF;
                color: #292524;
                border: 1px solid #D6D3D1;
                border-radius: 8px;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background: #0C0A09;
                color: #FFFFFF;
                border-color: #0C0A09;
            }
        """)
        self.calib_btn.clicked.connect(self.calibrate_requested.emit)
        actions_row.addWidget(self.calib_btn)

        self.switch_to_control_btn = QPushButton("🎮 Enter Air-Mouse Mode")
        self.switch_to_control_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.switch_to_control_btn.setFont(QFont("Inter", 10, QFont.Weight.DemiBold))
        self.switch_to_control_btn.setStyleSheet("""
            QPushButton {
                background: #F0EFED;
                color: #292524;
                border: 1px solid #E7E5E4;
                border-radius: 8px;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background: #2563EB;
                color: #FFFFFF;
                border-color: #2563EB;
            }
        """)
        self.switch_to_control_btn.clicked.connect(self._toggle_air_mouse)
        actions_row.addWidget(self.switch_to_control_btn)

        actions_row.addStretch(1)

        # Instruction hint
        self.hint_lbl = QLabel("Tip: Pinch thumb & index finger to left-click")
        self.hint_lbl.setFont(QFont("Inter", 10))
        self.hint_lbl.setStyleSheet("color: #777169; border: none; background: transparent;")
        actions_row.addWidget(self.hint_lbl)

        layout.addLayout(actions_row)

    def set_control_mode(self, active: bool):
        """Switches UI between Vision/Gaze mode and Air-Mouse Control mode."""
        self._is_control_mode = active
        if active:
            self.title_lbl.setText("🎮 Air-Mouse Computer Control")
            self.mode_badge.setText("● Air-Mouse Active")
            self.mode_badge.setStyleSheet("""
                color: #059669;
                background: #ECFDF5;
                border: 1px solid #A7F3D0;
                border-radius: 10px;
                padding: 2px 8px;
            """)
            self.switch_to_control_btn.setText("👁️ Switch to Vision Mode")
            self.hint_lbl.setText("Point index finger to move cursor · Pinch to click · Rock sign (🤘) to exit")
        else:
            self.title_lbl.setText("👁️ Vision & Attention HUD")
            self.mode_badge.setText("● Vision Active")
            self.mode_badge.setStyleSheet("""
                color: #7E22CE;
                background: #F5F3FF;
                border: 1px solid #DDD6FE;
                border-radius: 10px;
                padding: 2px 8px;
            """)
            self.switch_to_control_btn.setText("🎮 Enter Air-Mouse Mode")
            self.hint_lbl.setText("Gaze tracking active · Blink detection tracking attention")

    def _toggle_air_mouse(self):
        import asyncio
        if self._is_control_mode:
            asyncio.create_task(event_bus.publish("ENTER_CAMERA_MODE", {}))
        else:
            asyncio.create_task(event_bus.publish("ENTER_CONTROL_MODE", {}))

    def _toggle_camera_power(self):
        if self._is_camera_active:
            self.stop_camera_requested.emit()
            self._is_camera_active = False
            self.cam_toggle_btn.setText("📹 Turn On Camera")
            self.feed_lbl.setText("Camera Feed Paused")
            self.feed_lbl.setPixmap(QPixmap())
        else:
            self.start_camera_requested.emit()
            self._is_camera_active = True
            self.cam_toggle_btn.setText("📹 Turn Off Camera")
            self.feed_lbl.setText("Starting camera...")

    def update_frame(self, frame: np.ndarray):
        """Renders live RGB camera frame with landmark meshes onto video canvas."""
        self._is_camera_active = True
        lbl_w = self.feed_lbl.width()
        lbl_h = self.feed_lbl.height()

        if lbl_w > 10 and lbl_h > 10 and frame is not None:
            h, w, ch = frame.shape
            scale = min(lbl_w / float(w), lbl_h / float(h))
            new_w = max(int(w * scale), 1)
            new_h = max(int(h * scale), 1)
            resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

            h_r, w_r, ch = resized.shape
            bytes_per_line = ch * w_r
            q_img = QImage(resized.data, w_r, h_r, bytes_per_line, QImage.Format.Format_RGB888)
            self.feed_lbl.setPixmap(QPixmap.fromImage(q_img))

    def update_data(self, data: dict):
        """Updates live telemetry fields from MediaPipe and vision engines."""
        fps = data.get("fps", 0)
        self.fps_lbl.setText(f"FPS: {fps:.1f}")

        # Gaze & Eye telemetry
        gaze = data.get("gaze", {})
        direction = gaze.get("direction", "center").upper()
        self.gaze_lbl.setText(f"Gaze: {direction}")

        blink = data.get("blink", {})
        if blink.get("blink"):
            dur = blink.get("duration_ms", 0)
            self.blink_lbl.setText(f"Blink: {dur}ms")
        else:
            self.blink_lbl.setText("Blink: None")

        # Attention
        attention = data.get("attention", {})
        state = attention.get("attention_state", "FOCUSED").replace("USER_", "")
        self.attention_lbl.setText(f"Attention: {state.capitalize()}")

        # Gesture & Hand tracking
        gesture = data.get("gesture", {})
        g_name = gesture.get("type", "none")
        if g_name != "none":
            self.hand_lbl.setText(f"Gesture: {g_name.replace('_', ' ').title()}")
        else:
            self.hand_lbl.setText("Gesture: Tracking")
