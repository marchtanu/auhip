import asyncio
import numpy as np
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QStackedWidget,
    QApplication,
)
from PyQt6.QtCore import Qt

from auhip.core.event_bus import event_bus
import auhip.gui.theme as theme_module
from auhip.gui.theme import COLORS, STATE_COLORS
from auhip.gui.components.nav_bar import NavBar
from auhip.gui.components.ambient_voice_view import AmbientVoiceView
from auhip.gui.components.left_panel import LeftPanel
from auhip.gui.components.center_panel import CenterPanel
from auhip.gui.components.cockpit.cockpit_view import CockpitView


class AuhipMainWindow(QMainWindow):
    def __init__(self, fsm, mic=None, vision_worker=None, hide_on_standby=False, tts=None):
        super().__init__()
        self._fsm = fsm
        self._tts = tts
        self._vision_worker = vision_worker
        self._dark_mode = False
        self.hide_on_standby = hide_on_standby

        self.setWindowTitle("auhip")
        self.setMinimumSize(1260, 800)
        self.setStyleSheet(theme_module.STYLESHEET)

        self._build_ui()
        self._connect_events()

    def _build_ui(self):
        root = QWidget()
        root.setStyleSheet(f"background: {COLORS['bg']}; border: none;")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Nav Bar
        self.nav_bar = NavBar()
        root_layout.addWidget(self.nav_bar)

        # 2. Central Stacked View (Aesthetic HUD vs Functional Cockpit)
        self.stack = QStackedWidget()

        # Page 0: Aesthetic Voice View (Reference ChatGPT Voice visual)
        self.ambient_voice_view = AmbientVoiceView()
        self.ambient_voice_view.toggle_mode_requested.connect(self.toggle_ui_mode)
        self.stack.addWidget(self.ambient_voice_view)

        # Page 1: Next-Gen Cockpit View (White Editorial Aesthetic)
        self.cockpit_view = CockpitView(self._fsm, self._vision_worker)
        self.stack.addWidget(self.cockpit_view)

        # Legacy aliases for backwards compatibility with tests / handlers
        self.left_panel = self.cockpit_view.status_card
        self.center_panel = self.cockpit_view.conversation_workspace
        self.right_panel = self.cockpit_view.history_card
        self.debug_panel = self.cockpit_view.debug_drawer
        if self._tts:
            self.debug_panel.set_tts_instance(self._tts)
        if self._fsm and hasattr(self._fsm, 'speech_recognizer'):
            self.debug_panel.set_speech_recognizer(self._fsm.speech_recognizer)

        # Default to Aesthetic Voice HUD (Page 0) per test contract
        self.stack.setCurrentIndex(0)
        root_layout.addWidget(self.stack, 1)

        self.setCentralWidget(root)
        self._root_widget = root
        self._body_widget = self.cockpit_view

        self.set_ui_mode(0)

    def toggle_ui_mode(self):
        """Toggle between Page 0 (Aesthetic Voice HUD) and Page 1 (Functional Cockpit)."""
        new_index = 1 if self.stack.currentIndex() == 0 else 0
        self.set_ui_mode(new_index)

    def set_ui_mode(self, index: int):
        """Sets the active UI mode directly (0: Aesthetic HUD, 1: Cockpit)."""
        self.stack.setCurrentIndex(index)
        self.nav_bar.update_mode_button(index)
        if index == 0:
            # Voice HUD has its own floating top pill dock
            self.nav_bar.hide()
            self.debug_panel.hide()
        else:
            # Cockpit has full nav bar and debug controls
            self.nav_bar.show()
            self.debug_panel.show()

    def keyPressEvent(self, event):
        """Global shortcut Ctrl+Tab or F2 toggles between Voice HUD and Cockpit, Escape cancels."""
        if event.key() == Qt.Key.Key_F2 or (
            event.modifiers() == Qt.KeyboardModifier.ControlModifier
            and event.key() == Qt.Key.Key_Tab
        ):
            self.toggle_ui_mode()
            event.accept()
        elif event.key() == Qt.Key.Key_Escape:
            import asyncio
            from auhip.core.event_bus import event_bus
            asyncio.create_task(event_bus.publish("ENTER_SLEEP_MODE", {}))
            event.accept()
        else:
            super().keyPressEvent(event)


    def _connect_events(self):
        mappings = {
            "STATE_CHANGED":     self._on_state_changed,
            "MODE_CHANGED":      self._on_mode_changed,
            "SPEECH_RECOGNIZED": self._on_speech_recognized,
            "AUHIP_RESPONSE":    self._on_auhip_response,
            "COMMAND_EXECUTED":  self._on_command_executed,
            "SNAP_DETECTED":     self._on_snap,
            "HOME_ACTIVATED":    self._on_home_activated,
            "TOGGLE_VISION":     self._on_toggle_vision,
            "SET_VISION_STATE":  self._on_set_vision_state,
            "SET_EYE_STATE":     self._on_set_eye_state,
            "SET_HAND_STATE":    self._on_set_hand_state,
            "TOGGLE_FULLSCREEN": self._on_toggle_fullscreen,
            "MINIMIZE_WINDOW":   self._on_minimize_window,
            "APP_EXIT":          self._on_app_exit,
            "TOGGLE_THEME":      self._on_toggle_theme,
            "TOGGLE_UI_MODE":    self._on_toggle_ui_mode,
            "SET_UI_MODE":       self._on_set_ui_mode,
            "TTS_STARTED":       self._on_tts_started,
            "TTS_FINISHED":      self._on_tts_finished,
        }
        for event, handler in mappings.items():
            event_bus.subscribe(event, handler)

    # ── Theme Switching ───────────────────────────────────────────────────────

    async def _on_toggle_theme(self, data: dict):
        self._dark_mode = not self._dark_mode
        dark = self._dark_mode

        # Update shared theme dicts
        theme_module.set_theme(dark)
        theme_module._sync_state_colors(dark)

        # Update response colours for the transcript/response panels
        if dark:
            theme_module.RESPONSE_COLORS.update(theme_module.DARK_RESPONSE_COLORS)
        else:
            theme_module.RESPONSE_COLORS.update({
                "info":     "#6C6A64",
                "success":  "#5DB872",
                "warning":  "#E8A55A",
                "response": "#141413",
                "shutdown": "#C64545",
                "greeting": "#CC785C",
            })

        # Rebuild and apply the global stylesheet
        new_sheet = theme_module.build_stylesheet(dark)
        self.setStyleSheet(new_sheet)

        # Refresh root/body background colour
        self._root_widget.setStyleSheet(f"background: {COLORS['bg']}; border: none;")
        self._body_widget.setStyleSheet(f"background: {COLORS['bg']}; border: none;")

        # Delegate to individual panels that maintain their own stylesheets
        self.nav_bar.refresh_theme(dark)
        self.ambient_voice_view.set_dark_mode(dark)

    async def _on_toggle_ui_mode(self, data: dict):
        self.toggle_ui_mode()

    async def _on_set_ui_mode(self, data: dict):
        mode = data.get("mode", 0)
        idx = 1 if (mode == 1 or str(mode).lower() in ("cockpit", "functional")) else 0
        self.set_ui_mode(idx)


    # ── State Events ──────────────────────────────────────────────────────────

    async def _on_state_changed(self, data: dict):
        state, label = data["state"], data["label"]
        color = STATE_COLORS.get(state, COLORS["text_muted"])

        self.nav_bar.set_status(label, color)
        self.ambient_voice_view.set_status(state, label)
        self.cockpit_view.set_state(state, label)

        if state == "STANDBY" and self.hide_on_standby:
            self.hide()


    async def _on_mode_changed(self, data: dict):
        mode = data.get("mode", "")
        self.cockpit_view.handle_mode_changed(mode)

    async def _on_speech_recognized(self, data: dict):
        text = data.get("text", "")
        self.ambient_voice_view.show_transcript(text, is_user=True)
        self.cockpit_view.add_user_speech(text)

    async def _on_auhip_response(self, data: dict):
        text = data.get("text", "")
        self.ambient_voice_view.show_transcript(text, is_user=False)
        self.cockpit_view.add_assistant_response(text)

    async def _on_command_executed(self, data: dict):
        cmd = data.get("command", "")
        self.cockpit_view.add_command_history(cmd, data.get("response", ""))
        self.ambient_voice_view.set_last_command(cmd)

    async def _on_tts_started(self, data: dict):
        self.ambient_voice_view.set_speaking(True)
        self.cockpit_view.set_tts_active(True, speaking=True)
        if "clean_text" in data:
            self.ambient_voice_view.show_transcript(data["clean_text"], is_user=False)

    async def _on_tts_finished(self, data: dict):
        is_muted = getattr(self._tts, 'is_muted', False) if self._tts else False
        self.ambient_voice_view.set_speaking(False)
        self.cockpit_view.set_tts_active(not is_muted, speaking=False)

    async def _on_home_activated(self, data: dict):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    async def _on_toggle_vision(self, data: dict):
        if self.cockpit_view.center_deck.currentIndex() == 1:
            self.cockpit_view.switch_deck(0)
        else:
            self.cockpit_view.handle_mode_changed("CAMERA_MODE")

    async def _on_set_vision_state(self, data: dict):
        state = data.get("state", True)
        if state:
            self.cockpit_view.handle_mode_changed("CAMERA_MODE")
        else:
            self.cockpit_view.switch_deck(0)

    async def _on_toggle_fullscreen(self, data: dict):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    async def _on_minimize_window(self, data: dict):
        self.showMinimized()

    async def _on_set_eye_state(self, data: dict):
        state = data.get("state", True)
        if self._vision_worker:
            self._vision_worker.enable_eye_tracking = state
            status = "enabled" if state else "disabled"
            await event_bus.publish("AUHIP_RESPONSE", {"text": f"Eye tracking {status}.", "type": "info"})

    async def _on_set_hand_state(self, data: dict):
        state = data.get("state", True)
        if self._vision_worker:
            self._vision_worker.enable_hand_tracking = state
            status = "enabled" if state else "disabled"
            await event_bus.publish("AUHIP_RESPONSE", {"text": f"Hand tracking {status}.", "type": "info"})

    async def _on_app_exit(self, data: dict):
        self.close()
        QApplication.instance().quit()

    async def _on_snap(self, data: dict):
        # count=0 is a reset signal (e.g. sent when Voice Mode is entered)
        if data.get("count", -1) == 0:
            self._snap_count = 0
            self.cockpit_view.update_snaps(0)
            return
        if not hasattr(self, '_snap_count'): self._snap_count = 0
        self._snap_count = (self._snap_count % 2) + 1
        self.cockpit_view.update_snaps(self._snap_count)

    def feed_audio(self, chunk):
        self.ambient_voice_view.feed_audio(chunk)
        self.cockpit_view.feed_audio(chunk)
