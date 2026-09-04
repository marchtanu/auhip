import os
import sys
import unittest
import numpy as np

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtWidgets import QApplication

# Ensure QApplication instance exists
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from unittest.mock import MagicMock
from auhip.gui.components.cockpit.system_status_card import SystemStatusCard
from auhip.gui.components.cockpit.bento_cards import PrioritiesCard, InProgressCard, SystemOverviewCard
from auhip.gui.components.cockpit.action_chips import ContinueConversationBar
from auhip.gui.components.cockpit.conversation_workspace import ConversationWorkspace
from auhip.gui.components.cockpit.history_and_tasks import CommandHistoryCard, ActiveTasksCard
from auhip.gui.components.cockpit.debug_drawer import DebugControlsDrawer
from auhip.gui.components.cockpit.cockpit_view import CockpitView
from auhip.gui.main_window import AuhipMainWindow
from auhip.core.state_machine import AuhipStateMachine


from auhip.gui.components.cockpit.vision_control_hud import VisionControlHUD
from auhip.gui.components.cockpit.workspace_explorer import WorkspaceExplorer
from auhip.gui.components.cockpit.task_manager_modal import TaskManagerModal


class TestCockpitView(unittest.TestCase):
    def setUp(self):
        sr = MagicMock()
        agent = MagicMock()
        self.fsm = AuhipStateMachine(sr, agent)

    def test_system_status_card_creation(self):
        card = SystemStatusCard()
        self.assertIsNotNone(card)
        card.set_state("VOICE_MODE", "Voice Mode")
        card.update_snaps(1)
        card.update_snaps(2)
        card.update_snaps(0)
        # Test audio feed
        dummy_audio = np.zeros(512, dtype=np.float32)
        card.feed_audio(dummy_audio)

    def test_bento_cards_creation(self):
        p_card = PrioritiesCard()
        self.assertIsNotNone(p_card)

        ip_card = InProgressCard()
        self.assertIsNotNone(ip_card)

        s_card = SystemOverviewCard()
        self.assertIsNotNone(s_card)

    def test_action_chips_and_conversation_workspace(self):
        chips = ContinueConversationBar()
        self.assertIsNotNone(chips)

        conv = ConversationWorkspace()
        self.assertIsNotNone(conv)
        conv.add_user_message("Test user message")
        conv.add_assistant_message("Test assistant reply")
        conv.set_input_text("Hello AUHIP")
        self.assertEqual(conv.input_field.text(), "Hello AUHIP")

    def test_history_and_tasks_cards(self):
        hist = CommandHistoryCard()
        self.assertIsNotNone(hist)
        hist.add_command("Analyze project", "12:00 PM")

        tasks = ActiveTasksCard()
        self.assertIsNotNone(tasks)

    def test_debug_drawer(self):
        drawer = DebugControlsDrawer(self.fsm)
        self.assertIsNotNone(drawer)
        drawer._toggle_collapse()
        self.assertTrue(drawer.content_widget.isHidden())
        drawer._toggle_collapse()
        self.assertFalse(drawer.content_widget.isHidden())
        drawer.log_event("Test debug log")
        self.assertTrue(drawer.mic_enabled)

    def test_vision_control_hud(self):
        hud = VisionControlHUD()
        self.assertIsNotNone(hud)
        # Test mode setting
        hud.set_control_mode(True)
        self.assertTrue(hud._is_control_mode)
        self.assertIn("Air-Mouse", hud.title_lbl.text())
        hud.set_control_mode(False)
        self.assertFalse(hud._is_control_mode)
        self.assertIn("Vision", hud.title_lbl.text())

        # Test frame rendering with dummy RGB frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        hud.update_frame(frame)

        # Test data telemetry
        hud.update_data({
            "fps": 30.0,
            "gaze": {"direction": "center"},
            "blink": {"blink": True, "duration_ms": 180},
            "attention": {"attention_state": "FOCUSED"},
            "gesture": {"type": "pinch"},
        })
        self.assertIn("CENTER", hud.gaze_lbl.text())
        self.assertIn("Pinch", hud.hand_lbl.text())

    def test_workspace_explorer(self):
        exp = WorkspaceExplorer()
        self.assertIsNotNone(exp)
        self.assertGreater(exp.file_list.count(), 0)
        # Load main.py
        exp.load_file("main.py")
        self.assertIn("main.py", exp.file_path_lbl.text())
        self.assertIn("AuhipMainWindow", exp.code_viewer.toPlainText())

    def test_task_manager_modal(self):
        modal = TaskManagerModal()
        self.assertIsNotNone(modal)
        modal.refresh_tasks()

    def test_cockpit_view_deck_switching(self):
        view = CockpitView(self.fsm)
        self.assertIsNotNone(view)

        # Starts at Chat Workspace (Page 0)
        self.assertEqual(view.center_deck.currentIndex(), 0)

        # Switch to Vision HUD (Page 1)
        view.switch_deck(1)
        self.assertEqual(view.center_deck.currentIndex(), 1)

        # Switch to Workspace Explorer (Page 2)
        view.switch_deck(2)
        self.assertEqual(view.center_deck.currentIndex(), 2)

        # Auto-switch to Vision on CAMERA_MODE
        view.handle_mode_changed("CAMERA_MODE")
        self.assertEqual(view.center_deck.currentIndex(), 1)
        self.assertFalse(view.vision_hud._is_control_mode)

        # Auto-switch to Air-Mouse on CONTROL_MODE
        view.handle_mode_changed("CONTROL_MODE")
        self.assertEqual(view.center_deck.currentIndex(), 1)
        self.assertTrue(view.vision_hud._is_control_mode)

        # Auto-return to Chat on VOICE_MODE
        view.handle_mode_changed("VOICE_MODE")
        self.assertEqual(view.center_deck.currentIndex(), 0)

    def test_cockpit_guide_modal(self):
        from auhip.gui.components.cockpit.cockpit_guide_modal import CockpitGuideModal
        guide = CockpitGuideModal()
        self.assertIsNotNone(guide)
        self.assertEqual(guide.tabs.count(), 4)

    def test_main_window_with_cockpit(self):
        win = AuhipMainWindow(self.fsm)
        self.assertIsNotNone(win)
        self.assertEqual(win.stack.currentIndex(), 0)  # Voice HUD is default page 0
        win.toggle_ui_mode()
        self.assertEqual(win.stack.currentIndex(), 1)  # Cockpit is page 1
        win.toggle_ui_mode()
        self.assertEqual(win.stack.currentIndex(), 0)  # Back to Voice HUD


if __name__ == "__main__":
    unittest.main()
