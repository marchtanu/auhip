from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QCheckBox,
    QComboBox,
    QLineEdit,
    QTextEdit,
    QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from auhip.core.state_machine import State


class DebugControlsDrawer(QFrame):
    """
    Collapsible Bottom Drawer per reference visual:
    - Left: Hardware switches & Device selectors (Camera, Microphone)
    - Middle: Mode Override pills & Vision Toggles (Eyes, Hand, Pose, Gaze)
    - Center-Right: Prompt / Tool execution field with Run button
    - Right: Real-time Event Stream monitor
    """

    mode_selected = pyqtSignal(str)
    tool_run_requested = pyqtSignal(str)
    vision_toggle_requested = pyqtSignal(str, bool)
    mic_toggled = pyqtSignal(bool)
    tts_toggled = pyqtSignal(bool)

    def __init__(self, fsm=None, parent=None):
        super().__init__(parent)
        self._fsm = fsm
        self._is_collapsed = False
        self.setStyleSheet("""
            DebugControlsDrawer {
                background: #FFFFFF;
                border: 1px solid #E7E5E4;
                border-radius: 16px;
            }
        """)
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 10, 14, 12)
        main_layout.setSpacing(8)

        # ── 1. Drawer Header Toggle ───────────────────────────────────────────
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)

        self.toggle_btn = QPushButton("DEBUG & CONTROLS  ∨")
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.setFont(QFont("Inter", 10, QFont.Weight.Bold))
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                color: #777169;
                background: transparent;
                border: none;
                letter-spacing: 0.6px;
                padding: 0;
            }
            QPushButton:hover {
                color: #0C0A09;
            }
        """)
        self.toggle_btn.clicked.connect(self._toggle_collapse)
        header_row.addWidget(self.toggle_btn)
        header_row.addStretch()

        main_layout.addLayout(header_row)

        # ── 2. Collapsible Content Container ──────────────────────────────────
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        c_layout = QHBoxLayout(self.content_widget)
        c_layout.setContentsMargins(0, 4, 0, 0)
        c_layout.setSpacing(14)

        # Col 1: Hardware & Device Selectors
        col1 = QVBoxLayout()
        col1.setSpacing(6)

        self.mic_chk = QCheckBox("Microphone enabled")
        self.mic_chk.setChecked(True)
        self.mic_chk.setFont(QFont("Inter", 10))
        self.mic_chk.setStyleSheet("color: #4E4E4E;")
        self.mic_chk.toggled.connect(self.mic_toggled.emit)
        col1.addWidget(self.mic_chk)

        self.tts_chk = QCheckBox("Voice output (TTS)")
        self.tts_chk.setChecked(True)
        self.tts_chk.setFont(QFont("Inter", 10))
        self.tts_chk.setStyleSheet("color: #4E4E4E;")
        self.tts_chk.toggled.connect(self.tts_toggled.emit)
        col1.addWidget(self.tts_chk)

        self.cam_combo = QComboBox()
        self.cam_combo.setStyleSheet(self._combo_style())
        self.cam_combo.addItem("HD Pro Webcam C920", 0)
        self.cam_combo.addItem("Integrated Camera", 1)
        col1.addWidget(self.cam_combo)

        self.mic_combo = QComboBox()
        self.mic_combo.setStyleSheet(self._combo_style())
        self.mic_combo.addItem("Default Microphone", "default")
        self.mic_combo.addItem("Microphone Array", "array")
        col1.addWidget(self.mic_combo)

        # STT Engine & Whisper Model Selector
        stt_row = QHBoxLayout()
        stt_row.setSpacing(4)
        stt_lbl = QLabel("STT:")
        stt_lbl.setFont(QFont("Inter", 9, QFont.Weight.Bold))
        stt_lbl.setStyleSheet("color: #777169;")
        stt_row.addWidget(stt_lbl)

        self.stt_combo = QComboBox()
        self.stt_combo.setStyleSheet(self._combo_style())
        self.stt_combo.addItem("Whisper (base.en)", "base.en")
        self.stt_combo.addItem("Whisper (small.en)", "small.en")
        self.stt_combo.addItem("Whisper (distil-small.en)", "distil-small.en")
        self.stt_combo.addItem("Whisper (turbo)", "turbo")
        self.stt_combo.addItem("Whisper (base)", "base")
        self.stt_combo.addItem("Vosk (offline)", "vosk")
        self.stt_combo.currentIndexChanged.connect(self._on_stt_model_changed)
        stt_row.addWidget(self.stt_combo, 1)
        col1.addLayout(stt_row)

        c_layout.addLayout(col1, 2)
        c_layout.addWidget(self._make_divider())

        # Col 2: Mode Override & Vision Toggles
        col2 = QVBoxLayout()
        col2.setSpacing(4)

        m_lbl = QLabel("MODE OVERRIDE")
        m_lbl.setFont(QFont("Inter", 9, QFont.Weight.Bold))
        m_lbl.setStyleSheet("color: #777169; letter-spacing: 0.5px;")
        col2.addWidget(m_lbl)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(6)
        for name in ["Voice", "Vision", "Control", "Sleep"]:
            btn = QPushButton(name)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFont(QFont("Inter", 10, QFont.Weight.Medium))
            btn.setStyleSheet("""
                QPushButton {
                    background: #F0EFED;
                    color: #292524;
                    border: 1px solid #E7E5E4;
                    border-radius: 6px;
                    padding: 3px 8px;
                }
                QPushButton:hover {
                    background: #292524;
                    color: #FFFFFF;
                }
            """)
            btn.clicked.connect(lambda checked, m=name.lower(): self.mode_selected.emit(m))
            mode_row.addWidget(btn)
        col2.addLayout(mode_row)

        v_lbl = QLabel("VISION TOGGLES")
        v_lbl.setFont(QFont("Inter", 9, QFont.Weight.Bold))
        v_lbl.setStyleSheet("color: #777169; letter-spacing: 0.5px; margin-top: 4px;")
        col2.addWidget(v_lbl)

        v_grid = QHBoxLayout()
        v_grid.setSpacing(8)
        self.eye_chk = QCheckBox("Eyes")
        self.eye_chk.setChecked(True)
        self.eye_chk.setStyleSheet("color: #4E4E4E; font-size: 10px;")
        self.eye_chk.toggled.connect(lambda c: self.vision_toggle_requested.emit("eyes", c))
        v_grid.addWidget(self.eye_chk)

        self.hand_chk = QCheckBox("Hand")
        self.hand_chk.setChecked(True)
        self.hand_chk.setStyleSheet("color: #4E4E4E; font-size: 10px;")
        self.hand_chk.toggled.connect(lambda c: self.vision_toggle_requested.emit("hand", c))
        v_grid.addWidget(self.hand_chk)

        self.pose_chk = QCheckBox("Pose")
        self.pose_chk.setStyleSheet("color: #4E4E4E; font-size: 10px;")
        v_grid.addWidget(self.pose_chk)

        self.gaze_chk = QCheckBox("Gaze")
        self.gaze_chk.setStyleSheet("color: #4E4E4E; font-size: 10px;")
        v_grid.addWidget(self.gaze_chk)
        col2.addLayout(v_grid)

        c_layout.addLayout(col2, 3)
        c_layout.addWidget(self._make_divider())

        # Col 3: Prompt / Tool Runner
        col3 = QVBoxLayout()
        col3.setSpacing(4)

        p_lbl = QLabel("PROMPT / TOOL")
        p_lbl.setFont(QFont("Inter", 9, QFont.Weight.Bold))
        p_lbl.setStyleSheet("color: #777169; letter-spacing: 0.5px;")
        col3.addWidget(p_lbl)

        run_box = QHBoxLayout()
        run_box.setSpacing(6)

        self.tool_input = QLineEdit()
        self.tool_input.setPlaceholderText("Type prompt or tool command...")
        self.tool_input.setFont(QFont("Inter", 11))
        self.tool_input.setStyleSheet("""
            QLineEdit {
                background: #FAFAFA;
                border: 1px solid #E7E5E4;
                border-radius: 6px;
                padding: 4px 8px;
                color: #0C0A09;
            }
            QLineEdit:focus {
                border: 1px solid #0C0A09;
                background: #FFFFFF;
            }
        """)
        self.tool_input.returnPressed.connect(self._run_tool)
        run_box.addWidget(self.tool_input, 1)

        run_btn = QPushButton("▷ Run")
        run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        run_btn.setFont(QFont("Inter", 10, QFont.Weight.DemiBold))
        run_btn.setStyleSheet("""
            QPushButton {
                background: #292524;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 5px 12px;
            }
            QPushButton:hover {
                background: #0C0A09;
            }
        """)
        run_btn.clicked.connect(self._run_tool)
        run_box.addWidget(run_btn)
        col3.addLayout(run_box)

        # Quick wake phrase info
        info_lbl = QLabel("Wake phrase: <b>daddy home</b> · Barge-In: <b>Active</b>")
        info_lbl.setFont(QFont("Inter", 9))
        info_lbl.setStyleSheet("color: #777169;")
        col3.addWidget(info_lbl)

        c_layout.addLayout(col3, 3)
        c_layout.addWidget(self._make_divider())

        # Col 4: Event Stream
        col4 = QVBoxLayout()
        col4.setSpacing(4)

        evt_hdr = QHBoxLayout()
        e_lbl = QLabel("EVENT STREAM")
        e_lbl.setFont(QFont("Inter", 9, QFont.Weight.Bold))
        e_lbl.setStyleSheet("color: #777169; letter-spacing: 0.5px;")
        evt_hdr.addWidget(e_lbl)
        evt_hdr.addStretch()

        live_lbl = QLabel("● Live")
        live_lbl.setFont(QFont("Inter", 9, QFont.Weight.Bold))
        live_lbl.setStyleSheet("color: #16A34A;")
        evt_hdr.addWidget(live_lbl)
        col4.addLayout(evt_hdr)

        self.event_log = QTextEdit()
        self.event_log.setReadOnly(True)
        self.event_log.setFixedHeight(60)
        self.event_log.setStyleSheet("""
            QTextEdit {
                background: #FAFAFA;
                border: 1px solid #E7E5E4;
                border-radius: 6px;
                color: #4E4E4E;
                font-family: 'Consolas', 'JetBrains Mono', monospace;
                font-size: 10px;
                padding: 2px 4px;
            }
        """)
        self.event_log.setPlainText(
            "12:45:30 State changed: Voice Mode\n"
            "12:45:29 TTS: Ready\n"
            "12:45:28 Microphone: Active\n"
            "12:45:27 Snap detected (1)"
        )
        col4.addWidget(self.event_log)

        c_layout.addLayout(col4, 3)

        main_layout.addWidget(self.content_widget)

    def _make_divider(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setStyleSheet("background: #E7E5E4; border: none; max-width: 1px;")
        return line

    def _combo_style(self) -> str:
        return """
            QComboBox {
                background: #FAFAFA;
                border: 1px solid #E7E5E4;
                border-radius: 6px;
                padding: 2px 8px;
                color: #292524;
                font-size: 10px;
                min-height: 20px;
            }
            QComboBox:hover {
                border-color: #D6D3D1;
            }
            QComboBox::drop-down {
                border: none;
                width: 16px;
            }
        """

    def _toggle_collapse(self):
        self._is_collapsed = not self._is_collapsed
        self.content_widget.setVisible(not self._is_collapsed)
        arrow = "∧" if self._is_collapsed else "∨"
        self.toggle_btn.setText(f"DEBUG & CONTROLS  {arrow}")

    def _run_tool(self):
        txt = self.tool_input.text().strip()
        if txt:
            self.tool_run_requested.emit(txt)
            self.log_event(f"Run: {txt}")
            self.tool_input.clear()

    def log_event(self, text: str):
        t = datetime.now().strftime("%H:%M:%S")
        self.event_log.append(f"{t} {text}")
        self.event_log.verticalScrollBar().setValue(
            self.event_log.verticalScrollBar().maximum()
        )

    # ── Hardware Instance Bindings ───────────────────────────────────────────

    @property
    def mic_enabled(self) -> bool:
        return self.mic_chk.isChecked()

    def set_mic_instance(self, mic):
        self._mic_instance = mic

    def set_tts_instance(self, tts):
        self._tts_instance = tts
        if self._tts_instance and hasattr(self, 'tts_chk'):
            self.tts_chk.setChecked(not getattr(self._tts_instance, 'is_muted', False))

    def set_speech_recognizer(self, sr):
        self._speech_recognizer = sr

    def _on_stt_model_changed(self, index: int):
        val = self.stt_combo.currentData()
        self.log_event(f"STT Model changed: {val}")
        from auhip.core.config import config
        if val == "vosk":
            config.STT_ENGINE = "vosk"
        else:
            config.STT_ENGINE = "whisper"
            config.WHISPER_MODEL_SIZE = val
            if hasattr(self, '_speech_recognizer') and self._speech_recognizer:
                import threading
                threading.Thread(
                    target=self._speech_recognizer.switch_whisper_model,
                    args=(val,),
                    daemon=True
                ).start()
