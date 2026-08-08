from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGraphicsDropShadowEffect
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QColor
from auhip.gui.theme import COLORS
from auhip.core.event_bus import event_bus


class CommandWidget(QFrame):
    def __init__(self, name, desc, trigger):
        super().__init__()
        self.base_style = (
            f"background: {COLORS['panel_soft']}; border-radius: 8px; "
            f"border: 1px solid {COLORS['border']};"
        )
        self.setStyleSheet(self.base_style)

        # Glow Effect
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(0)
        self._shadow.setOffset(0, 0)
        self._shadow.setColor(QColor(COLORS['accent']))
        self.setGraphicsEffect(self._shadow)

        cl = QVBoxLayout(self)
        cl.setContentsMargins(12, 10, 12, 10)
        cl.setSpacing(3)

        self.name_lbl = QLabel(name)
        self.name_lbl.setStyleSheet(
            f"color: {COLORS['accent']}; font-size: 13px; font-weight: 600; border: none; letter-spacing: -0.1px;"
        )

        self.desc_lbl = QLabel(desc)
        self.desc_lbl.setStyleSheet(
            f"color: {COLORS['text_body']}; font-size: 12px; border: none;"
        )

        self.trigger_lbl = QLabel(f"Trigger: {trigger}")
        self.trigger_lbl.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 11px; font-style: italic; border: none;"
        )

        cl.addWidget(self.name_lbl)
        cl.addWidget(self.desc_lbl)
        cl.addWidget(self.trigger_lbl)

        # Pulse highlight animation state (for one-off triggers)
        self._highlight_step = 0
        self._highlight_timer = QTimer(self)
        self._highlight_timer.setInterval(30)
        self._highlight_timer.timeout.connect(self._animate_highlight)

        # Continuous glow animation state (for held gestures)
        self._glowing = False
        self._glow_step = 2.0
        self._glow_increasing = True
        self._glow_timer = QTimer(self)
        self._glow_timer.setInterval(40)
        self._glow_timer.timeout.connect(self._animate_glow)

    def trigger_highlight(self):
        if not self._glowing:
            self._highlight_step = 6
            self._highlight_timer.start()

    def set_glowing(self, active: bool):
        if active == self._glowing:
            return
        self._glowing = active
        if active:
            self._highlight_timer.stop()
            self._glow_step = 2.0
            self._glow_increasing = True
            self._glow_timer.start()
        else:
            self._glow_timer.stop()
            self._shadow.setBlurRadius(0)
            self.setStyleSheet(self.base_style)

    def _animate_glow(self):
        if self._glow_increasing:
            self._glow_step += 0.3
            if self._glow_step >= 5.0:
                self._glow_increasing = False
        else:
            self._glow_step -= 0.3
            if self._glow_step <= 2.0:
                self._glow_increasing = True

        alpha = int(40 + 100 * (self._glow_step / 5.0))
        glow_color = QColor(COLORS['accent'])
        glow_color.setAlpha(alpha)

        self._shadow.setBlurRadius(self._glow_step * 4)
        self._shadow.setColor(glow_color)
        self.setStyleSheet(self.base_style + f" border: 1px solid {COLORS['accent']};")

    def _animate_highlight(self):
        if self._highlight_step <= 0:
            self._highlight_timer.stop()
            self._shadow.setBlurRadius(0)
            self.setStyleSheet(self.base_style)
            return

        if not self._glowing:
            alpha = int(200 * (self._highlight_step / 6.0))
            glow_color = QColor(COLORS['accent'])
            glow_color.setAlpha(alpha)
            self._shadow.setBlurRadius(self._highlight_step * 3)
            self._shadow.setColor(glow_color)
            self.setStyleSheet(self.base_style + f" border: 1px solid {COLORS['accent']};")

        self._highlight_step -= 1

    def refresh_theme(self):
        self.base_style = (
            f"background: {COLORS['panel_soft']}; border-radius: 8px; "
            f"border: 1px solid {COLORS['border']};"
        )
        self.setStyleSheet(self.base_style)
        self._shadow.setColor(QColor(COLORS['accent']))
        self.name_lbl.setStyleSheet(
            f"color: {COLORS['accent']}; font-size: 13px; font-weight: 600; border: none; letter-spacing: -0.1px;"
        )
        self.desc_lbl.setStyleSheet(
            f"color: {COLORS['text_body']}; font-size: 12px; border: none;"
        )
        self.trigger_lbl.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 11px; font-style: italic; border: none;"
        )
        if self._glowing:
            alpha = int(40 + 100 * (self._glow_step / 5.0))
            glow_color = QColor(COLORS['accent'])
            glow_color.setAlpha(alpha)
            self._shadow.setBlurRadius(self._glow_step * 4)
            self._shadow.setColor(glow_color)
            self.setStyleSheet(self.base_style + f" border: 1px solid {COLORS['accent']};")


class ActiveCommandsPanel(QFrame):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("QFrame { background: transparent; border: none; }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.header = QLabel("Active Commands")
        self.header.setStyleSheet(
            f"color: {COLORS['text']}; font-size: 14px; font-weight: 600; letter-spacing: -0.1px; border: none;"
        )
        layout.addWidget(self.header)

        self.commands_layout = QVBoxLayout()
        self.commands_layout.setSpacing(8)
        layout.addLayout(self.commands_layout)

        self._cmd_widgets = {}

        self._populate_commands("STANDBY")

        event_bus.subscribe("MODE_CHANGED", self._on_mode_changed)
        event_bus.subscribe("LAST_COMMAND", self._on_last_command)

        # Continuous command subscriptions
        event_bus.subscribe("TEMP_VOICE_START", lambda _: self._set_glow("Temp Voice", True))
        event_bus.subscribe("TEMP_VOICE_END",   lambda _: self._set_glow("Temp Voice", False))
        event_bus.subscribe("CURSOR_HOLD_START",lambda _: self._set_glow("Hold / Drag", True))
        event_bus.subscribe("CURSOR_HOLD_END",  lambda _: self._set_glow("Hold / Drag", False))

    async def _on_mode_changed(self, data: dict):
        mode = data.get("mode", "STANDBY")
        self._populate_commands(mode)

    def _set_glow(self, key: str, active: bool):
        if key in self._cmd_widgets:
            self._cmd_widgets[key].set_glowing(active)

    async def _on_last_command(self, data: dict):
        label = data.get("label", "")

        key = None
        if "Volume" in label:
            key = "Volume Up/Down"
        elif "Track" in label:
            key = "Next / Prev Track"
        elif "Play" in label or "Pause" in label:
            key = "Play / Pause"
        elif "Click" in label:
            key = "Click"

        if key and key in self._cmd_widgets:
            self._cmd_widgets[key].trigger_highlight()

    def _populate_commands(self, mode: str):
        # Clear existing commands
        while self.commands_layout.count():
            item = self.commands_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        mode_commands = {
            "STANDBY": [
                ("Activate", "Start voice mode", "2 Snaps + 'daddy home'"),
                ("Exit", "Close application", "2 Snaps + 'exit'"),
                ("Emergency Exit", "Close application", "Open Palm -> Fist"),
            ],
            "SLEEP": [
                ("Activate", "Start voice mode", "2 Snaps + 'daddy home'"),
                ("Exit", "Close application", "2 Snaps + 'exit'"),
                ("Emergency Exit", "Close application", "Open Palm -> Fist"),
            ],
            "VOICE_MODE": [
                ("Camera Mode", "Enable gesture control", "'open camera'"),
                ("Control Mode", "Enable cursor control", "'control on'"),
                ("Sleep Mode", "Enter standby", "'goodbye jojo' / 'goodnight'"),
                ("Minimize", "Minimize window", "'minimize window'"),
                ("Fullscreen", "Toggle fullscreen", "'fullscreen'"),
                ("Help", "List all voice commands", "'help'"),
            ],
            "CAMERA_MODE": [
                ("Temp Voice", "Listen while held", "Index finger up"),
                ("Play / Pause", "Toggle media", "Open Palm -> Fist"),
                ("Volume Up/Down", "Adjust volume", "3 fingers up/down"),
                ("Next / Prev Track", "Skip media", "3 fingers Point Left/Right"),
                ("Exit", "Return to Voice Mode", "'vision off'"),
            ],
            "CONTROL_MODE": [
                ("Move Cursor", "Follow hand position", "3 fingers up"),
                ("Click", "Mouse click", "Tap Index & Middle to Thumb"),
                ("Hold / Drag", "Mouse drag", "Hold Index & Middle to Thumb"),
                ("Double Click", "Fast double click", "Click gesture twice"),
                ("Blink Click", "Eye click", "Blink twice"),
                ("Exit", "Return to Voice Mode", "Rock Sign / 'control off'"),
            ],
        }

        if mode in ("PROCESSING", "WAITING_WAKE_WORD", "SNAP_DETECTED"):
            return

        commands = mode_commands.get(mode, [])

        mode_label = mode.replace('_', ' ').title()
        self.header.setText(f"Active Commands ({mode_label})")

        self._cmd_widgets.clear()

        for name, desc, trigger in commands:
            cmd_widget = CommandWidget(name, desc, trigger)
            self._cmd_widgets[name] = cmd_widget
            self.commands_layout.addWidget(cmd_widget)

    def refresh_theme(self):
        self.header.setStyleSheet(
            f"color: {COLORS['text']}; font-size: 14px; font-weight: 600; letter-spacing: -0.1px; border: none;"
        )
        for cmd_widget in self._cmd_widgets.values():
            cmd_widget.refresh_theme()


