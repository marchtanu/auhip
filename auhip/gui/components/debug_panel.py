import asyncio
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QCheckBox, QComboBox, QLineEdit
)
from PyQt6.QtCore import Qt
from auhip.gui.theme import COLORS
from auhip.core.event_bus import event_bus
from auhip.core.state_machine import State


class DebugPanel(QWidget):
    def __init__(self, fsm, parent=None):
        super().__init__(parent)
        self._fsm = fsm
        self._mic_instance = None # Set later
        self._mic_enabled = True

        # Dark card styling (Claude code-window-card aesthetic)
        self.setStyleSheet(
            f"QWidget {{ background: {COLORS['dark_card']}; border-top: 1px solid {COLORS['border_dark']};"
            "border-radius: 0; }"
        )
        self.setFixedHeight(180) # Increased height for hardware selectors

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(20)

        # Left: title + mic toggle
        left = QWidget()
        left.setStyleSheet("background: transparent; border: none;")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        self.title = QLabel("Developer tools")
        self.title.setStyleSheet(
            f"color: {COLORS['text_on_dark']}; font-size: 13px; font-weight: 600;"
            "letter-spacing: -0.1px;"
        )
        left_layout.addWidget(self.title)

        self._mic_check = QCheckBox("Microphone enabled")
        self._mic_check.setChecked(True)
        self._mic_check.setStyleSheet(
            f"color: {COLORS['text_on_dark_muted']}; font-size: 12px; spacing: 6px;"
        )
        self._mic_check.toggled.connect(self._toggle_mic)
        left_layout.addWidget(self._mic_check)
        
        # Hardware Selection
        self.hw_label = QLabel("Hardware")
        self.hw_label.setStyleSheet(f"color: {COLORS['text_on_dark_muted']}; font-size: 11px; margin-top: 5px;")
        left_layout.addWidget(self.hw_label)
        
        self.cam_select = QComboBox()
        self.cam_select.setStyleSheet(self._combo_style())
        left_layout.addWidget(self.cam_select)
        
        self.mic_select = QComboBox()
        self.mic_select.setStyleSheet(self._combo_style())
        left_layout.addWidget(self.mic_select)
        
        self._populate_hardware()
        
        self.cam_select.currentIndexChanged.connect(self._on_cam_changed)
        self.mic_select.currentIndexChanged.connect(self._on_mic_changed)

        left_layout.addStretch()
        left.setFixedWidth(160)
        layout.addWidget(left)

        # Divider
        self.div1 = QWidget()
        self.div1.setFixedWidth(1)
        self.div1.setStyleSheet(f"background: {COLORS['border_dark']}; border: none;")
        layout.addWidget(self.div1)

        # Center: action buttons -> Essential Buttons
        btn_area = QWidget()
        btn_area.setStyleSheet("background: transparent; border: none;")
        btn_layout_outer = QVBoxLayout(btn_area)
        btn_layout_outer.setContentsMargins(0, 0, 0, 0)
        btn_layout_outer.setSpacing(10)

        # 1. Mode Row
        mode_container = QWidget()
        mode_layout = QHBoxLayout(mode_container)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(6)
        
        self.mode_lbl = QLabel("Mode")
        self.mode_lbl.setFixedWidth(50)
        self.mode_lbl.setStyleSheet(f"color: {COLORS['text_on_dark_muted']}; font-size: 11px; text-transform: uppercase;")
        mode_layout.addWidget(self.mode_lbl)

        self._mode_btns = {}
        for text, state in [("Voice", State.VOICE_MODE), ("Vision", State.CAMERA_MODE), 
                            ("Control", State.CONTROL_MODE), ("Sleep", State.SLEEP)]:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, s=state: self._on_mode_btn_clicked(s))
            mode_layout.addWidget(btn)
            self._mode_btns[state] = btn
        
        btn_layout_outer.addWidget(mode_container)

        # 2. Plus Features Row
        feat_container = QWidget()
        feat_layout = QHBoxLayout(feat_container)
        feat_layout.setContentsMargins(0, 0, 0, 0)
        feat_layout.setSpacing(6)

        self.feat_lbl = QLabel("Feature")
        self.feat_lbl.setFixedWidth(50)
        self.feat_lbl.setStyleSheet(f"color: {COLORS['text_on_dark_muted']}; font-size: 11px; text-transform: uppercase;")
        feat_layout.addWidget(self.feat_lbl)

        self._btn_eyes = self._add_toggle_btn(feat_layout, "Eyes", self._toggle_eyes)
        self._btn_hands = self._add_toggle_btn(feat_layout, "Hand", self._toggle_hands, initial=True)
        self._btn_multi = self._add_toggle_btn(feat_layout, "Multi", self._toggle_multi)
        
        self._btn_shutdown = self._add_btn(feat_layout, "Shutdown", self._sim_shutdown, primary=False)
        
        feat_layout.addStretch()

        btn_layout_outer.addWidget(feat_container)

        # 3. Skills Row (Optional fallback)
        skill_container = QWidget()
        skill_layout = QHBoxLayout(skill_container)
        skill_layout.setContentsMargins(0, 0, 0, 0)
        skill_layout.setSpacing(6)

        self.skill_lbl = QLabel("Skill")
        self.skill_lbl.setFixedWidth(50)
        self.skill_lbl.setStyleSheet(f"color: {COLORS['text_on_dark_muted']}; font-size: 11px; text-transform: uppercase;")
        skill_layout.addWidget(self.skill_lbl)

        self.func_select = QComboBox()
        self.func_select.setStyleSheet(self._combo_style())
        if hasattr(self._fsm.agent, 'available_tools'):
            for name in sorted(self._fsm.agent.available_tools.keys()):
                self.func_select.addItem(name.replace('_', ' ').title(), name)
        
        self._exec_btn = QPushButton("Run")
        self._exec_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['border_dark']};
                border: 1px solid {COLORS['border_dark']};
                border-radius: 4px;
                color: {COLORS['text_on_dark']};
                padding: 2px 12px;
                font-size: 11px;
            }}
            QPushButton:hover {{ background-color: {COLORS['accent']}; color: white; }}
        """)
        self._exec_btn.clicked.connect(self._run_selected_func)
        
        skill_layout.addWidget(self.func_select, 1)
        skill_layout.addWidget(self._exec_btn)
        btn_layout_outer.addWidget(skill_container)

        # 3.5 Text Command Row — Direct keyboard input for noisy environments
        cmd_container = QWidget()
        cmd_layout = QHBoxLayout(cmd_container)
        cmd_layout.setContentsMargins(0, 0, 0, 0)
        cmd_layout.setSpacing(6)

        self.cmd_lbl = QLabel("Command")
        self.cmd_lbl.setFixedWidth(50)
        self.cmd_lbl.setStyleSheet(f"color: {COLORS['text_on_dark_muted']}; font-size: 11px; text-transform: uppercase;")
        cmd_layout.addWidget(self.cmd_lbl)

        self._text_cmd_input = QLineEdit()
        self._text_cmd_input.setPlaceholderText("Type command (e.g. tell time, get weather, volume up, open browser)...")
        self._text_cmd_input.setStyleSheet(
            f"background: {COLORS['border_dark']}; border: 1px solid {COLORS['border_dark']};"
            f"border-radius: 4px; color: {COLORS['text_on_dark']}; font-size: 11px; padding: 2px 8px;"
        )
        self._text_cmd_input.returnPressed.connect(self._send_text_cmd)
        cmd_layout.addWidget(self._text_cmd_input, 1)

        self._send_cmd_btn = QPushButton("Send")
        self._send_cmd_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']}; border: none;
                border-radius: 4px; color: white;
                padding: 2px 12px; font-size: 11px;
            }}
            QPushButton:hover {{ background-color: {COLORS['accent_hover']}; }}
        """)
        self._send_cmd_btn.clicked.connect(self._send_text_cmd)
        cmd_layout.addWidget(self._send_cmd_btn)

        btn_layout_outer.addWidget(cmd_container)

        # 4. Settings Row — Wake phrase config
        cfg_container = QWidget()
        cfg_layout = QHBoxLayout(cfg_container)
        cfg_layout.setContentsMargins(0, 0, 0, 0)
        cfg_layout.setSpacing(6)

        self.cfg_lbl = QLabel("Config")
        self.cfg_lbl.setFixedWidth(50)
        self.cfg_lbl.setStyleSheet(f"color: {COLORS['text_on_dark_muted']}; font-size: 11px; text-transform: uppercase;")
        cfg_layout.addWidget(self.cfg_lbl)

        self.wake_lbl = QLabel("Wake phrase:")
        self.wake_lbl.setStyleSheet(f"color: {COLORS['text_on_dark_muted']}; font-size: 11px;")
        cfg_layout.addWidget(self.wake_lbl)

        from auhip.core.config import config as _cfg
        self._wake_input = QLineEdit(_cfg.WAKE_PHRASE)
        self._wake_input.setPlaceholderText("e.g. daddy home")
        self._wake_input.setStyleSheet(
            f"background: {COLORS['border_dark']}; border: 1px solid {COLORS['border_dark']};"
            f"border-radius: 4px; color: {COLORS['text_on_dark']}; font-size: 11px; padding: 2px 8px;"
        )
        self._wake_input.setFixedWidth(130)
        cfg_layout.addWidget(self._wake_input)

        self.save_btn = QPushButton("Apply")
        self.save_btn.setFixedWidth(48)
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']}; border: none;
                border-radius: 4px; color: white;
                padding: 2px 8px; font-size: 11px;
            }}
            QPushButton:hover {{ background-color: {COLORS['accent_hover']}; }}
        """)
        self.save_btn.clicked.connect(self._apply_wake_phrase)
        cfg_layout.addWidget(self.save_btn)

        cfg_layout.addStretch()
        btn_layout_outer.addWidget(cfg_container)

        btn_layout_outer.addStretch()
        layout.addWidget(btn_area, 1)

        # Subscribe to mode changes to keep UI in sync
        event_bus.subscribe("MODE_CHANGED", self._on_mode_changed_event)
        
        # Initial state sync
        self._update_ui_states()

        # Divider
        self.div2 = QWidget()
        self.div2.setFixedWidth(1)
        self.div2.setStyleSheet(f"background: {COLORS['border_dark']}; border: none;")
        layout.addWidget(self.div2)

        # Right: event log
        log_area = QWidget()
        log_area.setStyleSheet("background: transparent; border: none;")
        log_layout = QVBoxLayout(log_area)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_layout.setSpacing(4)

        self.log_title = QLabel("Event log")
        self.log_title.setStyleSheet(
            f"color: {COLORS['text_on_dark_muted']}; font-size: 11px; letter-spacing: 0.3px;"
        )
        log_layout.addWidget(self.log_title)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setStyleSheet(f"""
            QTextEdit {{
                background: transparent;
                border: none;
                color: {COLORS['text_on_dark_muted']};
                font-family: 'Consolas', 'JetBrains Mono', monospace;
                font-size: 11px;
                padding: 0;
            }}
        """)
        log_layout.addWidget(self._log, 1)
        log_area.setFixedWidth(300)
        layout.addWidget(log_area)

    def _add_btn(self, layout, text: str, callback, primary: bool = False):
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if primary:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['accent']};
                    border: none;
                    border-radius: 6px;
                    color: #FFFFFF;
                    padding: 6px 14px;
                    font-size: 12px;
                    font-weight: 500;
                }}
                QPushButton:hover {{ background-color: {COLORS['accent_hover']}; }}
                QPushButton:pressed {{ background-color: #8E4A32; }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['border_dark']};
                    border: 1px solid {COLORS['border_dark']};
                    border-radius: 6px;
                    color: {COLORS['text_on_dark_muted']};
                    padding: 6px 14px;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: #2E2B27;
                    color: {COLORS['text_on_dark']};
                }}
                QPushButton:pressed {{ color: {COLORS['accent']}; }}
            """)
        btn.clicked.connect(callback)
        layout.addWidget(btn)
        return btn

    def _log_event(self, msg: str):
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        self._log.append(
            f'<span style="color:{COLORS["text_on_dark_muted"]};">[{ts}]</span> '
            f'<span style="color:{COLORS["text_on_dark"]};">{msg}</span>'
        )

    def _run_async(self, coro):
        asyncio.create_task(coro)

    def _sim_toggle_vision(self):
        self._log_event("Simulated: TOGGLE VISION")
        self._run_async(event_bus.publish("TOGGLE_VISION", {}))

    def _sim_shutdown(self):
        self._log_event("Simulated: SHUTDOWN")
        self._run_async(self._fsm.simulate_shutdown())

    def _on_mode_btn_clicked(self, state):
        if self._fsm.state != state:
            self._log_event(f"Forcing State -> {state.name}")
            
            # Map states to their proper entry methods
            if state == State.VOICE_MODE:
                self._run_async(self._fsm._enter_voice_mode())
            elif state == State.CAMERA_MODE:
                self._run_async(self._fsm._on_enter_camera_mode({}))
            elif state == State.CONTROL_MODE:
                self._run_async(self._fsm._on_enter_control_mode({}))
            elif state == State.SLEEP:
                self._run_async(self._fsm._enter_sleep_mode())
            else:
                self._fsm.state = state
                self._run_async(self._fsm._publish_state(f"Debug: Switch to {state.name}"))
        self._update_ui_states()

    def _add_toggle_btn(self, layout, text, callback, initial=False):
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setChecked(initial)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(callback)
        layout.addWidget(btn)
        return btn

    def _toggle_feature(self, event_name, label, checked):
        self._log_event(f"{label}: {'ON' if checked else 'OFF'}")
        self._run_async(event_bus.publish(event_name, {"state": checked}))
        self._update_ui_states()

    def _toggle_eyes(self, checked): self._toggle_feature("SET_EYE_STATE", "Eyes", checked)
    def _toggle_hands(self, checked): self._toggle_feature("SET_HAND_STATE", "Hand", checked)
    def _toggle_multi(self, checked): self._toggle_feature("SET_MULTI_HAND", "Multi-Hand", checked)

    def _run_selected_func(self):
        func_name = self.func_select.currentData()
        if func_name:
            self._log_event(f"Manual Skill Exec: {func_name}")
            func = self._fsm.agent.available_tools.get(func_name)
            if func:
                self._run_async(func())

    def _send_text_cmd(self):
        text = self._text_cmd_input.text().strip()
        if text:
            self._log_event(f"Text Cmd: '{text}'")
            self._text_cmd_input.clear()
            self._run_async(event_bus.publish("SPEECH_RECOGNIZED", {"text": text}))
            self._run_async(self._execute_text_cmd(text))

    async def _execute_text_cmd(self, text: str):
        if hasattr(self._fsm, 'agent') and self._fsm.agent:
            response = await self._fsm.agent.execute(text)
            if response:
                await event_bus.publish("AUHIP_RESPONSE", {
                    "text": response,
                    "type": "success"
                })
                await event_bus.publish("COMMAND_EXECUTED", {
                    "command": text,
                    "response": response
                })

    async def _on_mode_changed_event(self, data: dict):
        self._update_ui_states()

    def _update_ui_states(self):
        """Sync button styles with system state."""
        # Modes
        current_state = self._fsm.state
        for state, btn in self._mode_btns.items():
            btn.setChecked(state == current_state)
            btn.setStyleSheet(self._get_btn_style(state == current_state))

        # Features
        for btn in [self._btn_eyes, self._btn_hands, self._btn_multi]:
            btn.setStyleSheet(self._get_btn_style(btn.isChecked()))

    def _get_btn_style(self, active: bool):
        if active:
            return f"""
                QPushButton {{
                    background-color: {COLORS['accent']};
                    border: 1px solid {COLORS['accent']};
                    border-radius: 4px;
                    color: white;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: 600;
                }}
            """
        return f"""
            QPushButton {{
                background-color: {COLORS['border_dark']};
                border: 1px solid {COLORS['border_dark']};
                border-radius: 4px;
                color: {COLORS['text_on_dark_muted']};
                padding: 4px 10px;
                font-size: 11px;
            }}
            QPushButton:hover {{ background-color: #2E2B27; color: {COLORS['text_on_dark']}; }}
        """

    def _toggle_mic(self, enabled: bool):
        self._mic_enabled = enabled
        self._log_event(f"Microphone: {'ON' if enabled else 'OFF'}")

    def _combo_style(self):
        return f"""
            QComboBox {{
                background-color: {COLORS['border_dark']};
                border: 1px solid {COLORS['border_dark']};
                border-radius: 4px;
                color: {COLORS['text_on_dark']};
                padding: 2px 8px;
                font-size: 11px;
            }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['dark_card']};
                color: {COLORS['text_on_dark']};
                selection-background-color: {COLORS['accent']};
            }}
        """

    def _populate_hardware(self):
        # Mics
        import sounddevice as sd
        try:
            devices = sd.query_devices()
            for i, d in enumerate(devices):
                if d['max_input_channels'] > 0:
                    self.mic_select.addItem(f"Mic {i}: {d['name'][:20]}...", i)
        except Exception:
            self.mic_select.addItem("No Mics Found", -1)

        # Cameras
        import cv2
        for i in range(3): # Probe first 3
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                self.cam_select.addItem(f"Camera {i}", i)
                cap.release()
        if self.cam_select.count() == 0:
            self.cam_select.addItem("No Cameras Found", -1)

    def _on_cam_changed(self, index):
        cam_idx = self.cam_select.currentData()
        if cam_idx != -1:
            from auhip.core.event_bus import event_bus
            self._run_async(event_bus.publish("SET_CAMERA_INDEX", {"index": cam_idx}))
            self._log_event(f"Switched to Camera {cam_idx}")

    def _on_mic_changed(self, index):
        mic_idx = self.mic_select.currentData()
        if mic_idx != -1 and self._mic_instance:
            self._log_event(f"Switching Microphone to index {mic_idx}...")
            self._mic_instance.stop()
            self._mic_instance.start(device_index=mic_idx)

    def _apply_wake_phrase(self):
        from auhip.core.config import config as _cfg
        new_phrase = self._wake_input.text().strip().lower()
        if new_phrase:
            _cfg.WAKE_PHRASE = new_phrase
            self._log_event(f"Wake phrase updated: '{new_phrase}'")
        else:
            self._wake_input.setText(_cfg.WAKE_PHRASE)
            self._log_event("Wake phrase unchanged (empty input).")

    def set_mic_instance(self, mic): self._mic_instance = mic
    def log(self, msg: str): self._log_event(msg)
    @property
    def mic_enabled(self) -> bool: return self._mic_enabled

    def refresh_theme(self):
        """Re-apply all colours after a theme switch."""
        self.setStyleSheet(
            f"QWidget {{ background: {COLORS['dark_card']}; border-top: 1px solid {COLORS['border_dark']};"
            "border-radius: 0; }}"
        )
        self.title.setStyleSheet(
            f"color: {COLORS['text_on_dark']}; font-size: 13px; font-weight: 600;"
            "letter-spacing: -0.1px;"
        )
        self._mic_check.setStyleSheet(
            f"color: {COLORS['text_on_dark_muted']}; font-size: 12px; spacing: 6px;"
        )
        self.hw_label.setStyleSheet(f"color: {COLORS['text_on_dark_muted']}; font-size: 11px; margin-top: 5px;")
        
        self.cam_select.setStyleSheet(self._combo_style())
        self.mic_select.setStyleSheet(self._combo_style())
        self.func_select.setStyleSheet(self._combo_style())
        
        self.div1.setStyleSheet(f"background: {COLORS['border_dark']}; border: none;")
        self.div2.setStyleSheet(f"background: {COLORS['border_dark']}; border: none;")
        
        self.mode_lbl.setStyleSheet(f"color: {COLORS['text_on_dark_muted']}; font-size: 11px; text-transform: uppercase;")
        self.feat_lbl.setStyleSheet(f"color: {COLORS['text_on_dark_muted']}; font-size: 11px; text-transform: uppercase;")
        self.skill_lbl.setStyleSheet(f"color: {COLORS['text_on_dark_muted']}; font-size: 11px; text-transform: uppercase;")
        self.cfg_lbl.setStyleSheet(f"color: {COLORS['text_on_dark_muted']}; font-size: 11px; text-transform: uppercase;")
        self.wake_lbl.setStyleSheet(f"color: {COLORS['text_on_dark_muted']}; font-size: 11px;")
        self.log_title.setStyleSheet(f"color: {COLORS['text_on_dark_muted']}; font-size: 11px; letter-spacing: 0.3px;")
        
        self._wake_input.setStyleSheet(
            f"background: {COLORS['border_dark']}; border: 1px solid {COLORS['border_dark']};"
            f"border-radius: 4px; color: {COLORS['text_on_dark']}; font-size: 11px; padding: 2px 8px;"
        )
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']}; border: none;
                border-radius: 4px; color: white;
                padding: 2px 8px; font-size: 11px;
            }}
            QPushButton:hover {{ background-color: {COLORS['accent_hover']}; }}
        """)
        
        self._exec_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['border_dark']};
                border: 1px solid {COLORS['border_dark']};
                border-radius: 4px;
                color: {COLORS['text_on_dark']};
                padding: 2px 12px;
                font-size: 11px;
            }}
            QPushButton:hover {{ background-color: {COLORS['accent']}; color: white; }}
        """)
        
        self._btn_shutdown.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['border_dark']};
                border: 1px solid {COLORS['border_dark']};
                border-radius: 6px;
                color: {COLORS['text_on_dark_muted']};
                padding: 6px 14px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: #2E2B27;
                color: {COLORS['text_on_dark']};
            }}
            QPushButton:pressed {{ color: {COLORS['accent']}; }}
        """)
        
        self._update_ui_states()
