import asyncio
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QButtonGroup,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from auhip.core.event_bus import event_bus
from .system_status_card import SystemStatusCard
from .bento_cards import PrioritiesCard, InProgressCard, SystemOverviewCard
from .action_chips import ContinueConversationBar
from .conversation_workspace import ConversationWorkspace
from .vision_control_hud import VisionControlHUD
from .workspace_explorer import WorkspaceExplorer
from .task_manager_modal import TaskManagerModal
from .cockpit_guide_modal import CockpitGuideModal
from .history_and_tasks import CommandHistoryCard, ActiveTasksCard
from .debug_drawer import DebugControlsDrawer


class CockpitView(QWidget):
    """
    Master Next-Gen Cockpit View capable of handling every capability:
    - 3-Column layout in white editorial aesthetic (docs/DESIGN.md)
    - Left: SystemStatusCard (State, Mic/TTS, Snaps, CPU/RAM/GPU, mini ambient orb)
    - Center Deck with auto-switching tabs:
        [ 💬 Chat Workspace ] [ 👁️ Vision & Attention HUD ] [ 📁 Workspace Explorer ]
    - Full Vision & Air-Mouse Control pipeline (live video, gaze vector, gestures, calibration)
    - Interactive Code & File Explorer (scan, view files, find unused)
    - Interactive Task Manager modal (connected to organizer storage)
    - Right: Command History & Active Tasks
    - Bottom: Collapsible Debug Controls Drawer
    """

    def __init__(self, fsm=None, vision_worker=None, parent=None):
        super().__init__(parent)
        self._fsm = fsm
        self._vision_worker = vision_worker
        self._task_modal = None
        self.setStyleSheet("CockpitView { background: #F5F5F5; border: none; }")
        self._build_ui()
        self._connect_internal_signals()
        self._connect_vision_worker()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 12, 14, 12)
        main_layout.setSpacing(10)

        # ── 1. Upper 3-Column Body ────────────────────────────────────────────
        columns_layout = QHBoxLayout()
        columns_layout.setContentsMargins(0, 0, 0, 0)
        columns_layout.setSpacing(12)

        # Left Column: System Status Card
        self.status_card = SystemStatusCard()
        columns_layout.addWidget(self.status_card)

        # Center Column: Bento row + Action chips + Deck Tabs + Center Stack Deck
        center_col = QVBoxLayout()
        center_col.setContentsMargins(0, 0, 0, 0)
        center_col.setSpacing(10)

        # Top Bento Cards Row (3 Cards)
        bento_row = QHBoxLayout()
        bento_row.setContentsMargins(0, 0, 0, 0)
        bento_row.setSpacing(10)

        self.priorities_card = PrioritiesCard()
        bento_row.addWidget(self.priorities_card, 1)

        self.in_progress_card = InProgressCard()
        bento_row.addWidget(self.in_progress_card, 1)

        self.system_card = SystemOverviewCard()
        bento_row.addWidget(self.system_card, 1)

        center_col.addLayout(bento_row)

        # Action Chips Row
        self.action_chips = ContinueConversationBar()
        center_col.addWidget(self.action_chips)

        # Deck Switcher Tabs Bar
        deck_tabs_row = QHBoxLayout()
        deck_tabs_row.setContentsMargins(0, 0, 0, 0)
        deck_tabs_row.setSpacing(8)

        self.tab_group = QButtonGroup(self)
        self.tab_group.setExclusive(True)

        self.tab_chat = self._create_deck_tab("💬 Chat Workspace", 0, True)
        self.tab_vision = self._create_deck_tab("👁️ Vision & Air-Mouse HUD", 1, False)
        self.tab_files = self._create_deck_tab("📁 Workspace Explorer", 2, False)

        deck_tabs_row.addWidget(self.tab_chat)
        deck_tabs_row.addWidget(self.tab_vision)
        deck_tabs_row.addWidget(self.tab_files)
        deck_tabs_row.addStretch(1)

        self.guide_btn = QPushButton("📖 User Guide & Shortcuts")
        self.guide_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.guide_btn.setFont(QFont("Inter", 10, QFont.Weight.Medium))
        self.guide_btn.setStyleSheet("""
            QPushButton {
                background: #FFFFFF;
                color: #292524;
                border: 1px solid #E7E5E4;
                border-radius: 9999px;
                padding: 4px 14px;
            }
            QPushButton:hover {
                background: #0C0A09;
                color: #FFFFFF;
                border-color: #0C0A09;
            }
        """)
        self.guide_btn.clicked.connect(self._open_guide_modal)
        deck_tabs_row.addWidget(self.guide_btn)

        center_col.addLayout(deck_tabs_row)

        # Center Stack Deck
        self.center_deck = QStackedWidget()

        # Page 0: Conversation Workspace
        self.conversation_workspace = ConversationWorkspace()
        self.center_deck.addWidget(self.conversation_workspace)

        # Page 1: Vision & Air-Mouse Control HUD
        self.vision_hud = VisionControlHUD()
        self.center_deck.addWidget(self.vision_hud)

        # Page 2: Workspace & Code Explorer
        self.workspace_explorer = WorkspaceExplorer()
        self.center_deck.addWidget(self.workspace_explorer)

        self.center_deck.setCurrentIndex(0)
        center_col.addWidget(self.center_deck, 1)

        columns_layout.addLayout(center_col, 1)

        # Right Column: Command History + Active Tasks
        right_col = QVBoxLayout()
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.setSpacing(10)

        self.history_card = CommandHistoryCard()
        right_col.addWidget(self.history_card, 1)

        self.tasks_card = ActiveTasksCard()
        right_col.addWidget(self.tasks_card, 1)

        right_widget = QWidget()
        right_widget.setFixedWidth(240)
        right_widget.setStyleSheet("background: transparent;")
        right_widget.setLayout(right_col)
        columns_layout.addWidget(right_widget)

        main_layout.addLayout(columns_layout, 1)

        # ── 2. Collapsible Bottom Debug Controls Drawer ───────────────────────
        self.debug_drawer = DebugControlsDrawer(self._fsm)
        main_layout.addWidget(self.debug_drawer)

    def _create_deck_tab(self, label: str, index: int, checked: bool = False) -> QPushButton:
        btn = QPushButton(label)
        btn.setCheckable(True)
        btn.setChecked(checked)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFont(QFont("Inter", 10, QFont.Weight.Medium))
        btn.setStyleSheet("""
            QPushButton {
                background: #FFFFFF;
                color: #777169;
                border: 1px solid #E7E5E4;
                border-radius: 9999px;
                padding: 4px 14px;
            }
            QPushButton:hover {
                background: #F0EFED;
                color: #0C0A09;
            }
            QPushButton:checked {
                background: #292524;
                color: #FFFFFF;
                border-color: #292524;
            }
        """)
        btn.clicked.connect(lambda: self.switch_deck(index))
        self.tab_group.addButton(btn, index)
        return btn

    def switch_deck(self, index: int):
        """Switches the active center workspace deck (0: Chat, 1: Vision, 2: Files)."""
        self.center_deck.setCurrentIndex(index)
        btn = self.tab_group.button(index)
        if btn and not btn.isChecked():
            btn.setChecked(True)

        # If switching away from vision, stop camera to conserve resources if not in camera mode
        if index != 1 and self._vision_worker:
            curr_state = getattr(self._fsm, 'current_state', None)
            from auhip.core.state_machine import State
            if curr_state not in (State.CAMERA_MODE, State.CONTROL_MODE):
                self._vision_worker.stop()

    def _connect_internal_signals(self):
        # Action chips forward prompt
        self.action_chips.prompt_selected.connect(self._on_action_chip_selected)

        # Prompt submissions forward to event bus
        self.conversation_workspace.prompt_submitted.connect(self._dispatch_user_prompt)
        self.debug_drawer.tool_run_requested.connect(self._dispatch_user_prompt)

        # Open file in workspace viewer from chat attachment pill
        self.conversation_workspace.open_file_requested.connect(self._open_file_in_explorer)

        # Open workspace from InProgress bento card
        self.in_progress_card.open_workspace_clicked.connect(lambda: self.switch_deck(2))

        # View tasks modal from Priorities & ActiveTasks cards
        self.priorities_card.view_tasks_clicked.connect(self._open_task_modal)
        self.tasks_card.view_tasks_clicked.connect(self._open_task_modal)

        # Close Vision HUD -> back to chat
        self.vision_hud.close_requested.connect(lambda: self.switch_deck(0))
        self.workspace_explorer.close_requested.connect(lambda: self.switch_deck(0))

        # History click-to-rerun
        self.history_card.view_history_clicked.connect(lambda: self._dispatch_user_prompt("list all recent command history"))

        # Mode overrides
        self.debug_drawer.mode_selected.connect(self._on_mode_override)

        # Hardware toggles
        self.debug_drawer.mic_toggled.connect(self._on_mic_toggle)
        self.debug_drawer.tts_toggled.connect(self._on_tts_toggle)
        self.debug_drawer.vision_toggle_requested.connect(self._on_vision_toggle)

    def _connect_vision_worker(self):
        """Binds the real-time vision worker signals to the VisionControlHUD."""
        if self._vision_worker:
            self._vision_worker.frame_ready.connect(self.vision_hud.update_frame)
            self._vision_worker.vision_data_ready.connect(self.vision_hud.update_data)
            self.vision_hud.calibrate_requested.connect(self._vision_worker.calibrate)
            self.vision_hud.start_camera_requested.connect(self._vision_worker.start)
            self.vision_hud.stop_camera_requested.connect(self._vision_worker.stop)

    def handle_mode_changed(self, mode_str: str):
        """Auto-switches to Vision & Control HUD when entering Camera or Control modes."""
        m = str(mode_str).upper()
        if "CAMERA" in m or "VISION" in m:
            self.switch_deck(1)
            self.vision_hud.set_control_mode(False)
            if self._vision_worker:
                self._vision_worker.start()
        elif "CONTROL" in m:
            self.switch_deck(1)
            self.vision_hud.set_control_mode(True)
            if self._vision_worker:
                self._vision_worker.start()
        elif "VOICE" in m or "STANDBY" in m:
            if self.center_deck.currentIndex() == 1:
                self.switch_deck(0)

    def _open_file_in_explorer(self, file_path: str):
        self.switch_deck(2)
        self.workspace_explorer.load_file(file_path)

    def _open_task_modal(self):
        self._task_modal = TaskManagerModal(self)
        self._task_modal.exec()

    def _open_guide_modal(self):
        guide = CockpitGuideModal(self)
        guide.exec()

    def _on_action_chip_selected(self, prompt: str):
        if "camera" in prompt.lower() or "vision" in prompt.lower():
            self.handle_mode_changed("CAMERA_MODE")
        else:
            self.conversation_workspace.set_input_text(prompt)
            self._dispatch_user_prompt(prompt)

    def _dispatch_user_prompt(self, prompt: str):
        self.debug_drawer.log_event(f"User: {prompt}")
        asyncio.create_task(event_bus.publish("PROCESS_COMMAND", {"command": prompt}))

    def _on_mode_override(self, mode: str):
        m = mode.upper()
        self.debug_drawer.log_event(f"Mode override: {m}")
        if m == "VOICE":
            asyncio.create_task(event_bus.publish("ENTER_VOICE_MODE", {}))
        elif m == "VISION":
            asyncio.create_task(event_bus.publish("ENTER_CAMERA_MODE", {}))
        elif m == "CONTROL":
            asyncio.create_task(event_bus.publish("ENTER_CONTROL_MODE", {}))
        elif m == "SLEEP":
            asyncio.create_task(event_bus.publish("ENTER_SLEEP_MODE", {}))

    def _on_mic_toggle(self, enabled: bool):
        self.status_card.mic_lbl.setText("Listening..." if enabled else "Mic disabled")
        self.debug_drawer.log_event(f"Microphone: {'Enabled' if enabled else 'Disabled'}")

    def _on_tts_toggle(self, enabled: bool):
        self.status_card.set_tts_active(enabled)
        self.debug_drawer.log_event(f"Voice Output (TTS): {'Enabled' if enabled else 'Disabled'}")

    def _on_vision_toggle(self, feature: str, enabled: bool):
        self.debug_drawer.log_event(f"Vision {feature}: {enabled}")
        if self._vision_worker:
            if feature == "eyes":
                self._vision_worker.enable_eye_tracking = enabled
            elif feature == "hand":
                self._vision_worker.enable_hand_tracking = enabled

    # ── Live Data Ingestion ───────────────────────────────────────────────────

    def feed_audio(self, chunk):
        """Pass audio chunk to the embedded mini ambient orb."""
        self.status_card.feed_audio(chunk)

    def set_state(self, state: str, label: str):
        self.status_card.set_state(state, label)
        self.debug_drawer.log_event(f"State changed: {label}")
        self.handle_mode_changed(state)

    def set_tts_active(self, active: bool, speaking: bool = False):
        self.status_card.set_tts_active(active, speaking=speaking)
        if speaking:
            self.debug_drawer.log_event("TTS: Speaking...")
        else:
            self.debug_drawer.log_event("TTS: Finished")

    def update_snaps(self, count: int):
        self.status_card.update_snaps(count)
        if count > 0:
            self.debug_drawer.log_event(f"Snap detected ({count})")

    def add_user_speech(self, text: str):
        self.conversation_workspace.add_user_message(text)
        self.debug_drawer.log_event(f"Heard: {text}")

    def add_assistant_response(self, text: str):
        self.conversation_workspace.add_assistant_message(text)

    def add_command_history(self, cmd: str, response: str = ""):
        self.history_card.add_command(cmd)
        self.debug_drawer.log_event(f"Command executed: {cmd}")
