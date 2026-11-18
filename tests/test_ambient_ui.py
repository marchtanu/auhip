import os
import sys
import unittest
import numpy as np

# Offscreen Qt for headless testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtWidgets import QApplication
from auhip.gui.components.ambient_orb_widget import AmbientOrbWidget
from auhip.gui.components.ambient_voice_view import AmbientVoiceView
from auhip.gui.main_window import AuhipMainWindow
from auhip.core.state_machine import AuhipStateMachine
from auhip.core.agent import AuhipAgent
from auhip.audio.speech_recognition import SpeechRecognizer


class TestAmbientVoiceUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_ambient_orb_widget(self):
        orb = AmbientOrbWidget()
        self.assertIsNotNone(orb)
        self.assertEqual(orb._current_energy, 0.0)

        # Simulate audio chunk
        sample_chunk = np.random.uniform(-0.5, 0.5, 1600).astype(np.float32)
        orb.update_audio(sample_chunk)
        self.assertGreater(orb._target_energy, 0.0)

        # Tick step
        orb._on_tick()
        self.assertGreater(orb._current_energy, 0.0)

        # Speaking state
        orb.set_speaking_state(True)
        self.assertTrue(orb._is_speaking)
        orb.set_speaking_state(False)
        self.assertFalse(orb._is_speaking)

    def test_ambient_voice_view(self):
        view = AmbientVoiceView()
        self.assertIsNotNone(view)

        # Status setting
        view.set_status("VOICE_MODE")
        self.assertIn("Listening", view.status_pill.text())

        view.set_status("PROCESSING")
        self.assertIn("Thinking", view.status_pill.text())

        view.set_speaking(True)
        self.assertIn("Speaking", view.status_pill.text())

        # Bottom transcript box/panel is removed, replaced with subtle typography heard_lbl
        self.assertFalse(hasattr(view, "transcript_card"))
        self.assertTrue(hasattr(view, "heard_lbl"))

        # When machine hears user speech, it should display at bottom
        view.show_transcript("what time is it", is_user=True)
        self.assertIn("what time is it", view.heard_lbl.text())


    def test_main_window_stack_and_toggle(self):
        sr = SpeechRecognizer()
        agent = AuhipAgent()
        fsm = AuhipStateMachine(sr, agent)
        window = AuhipMainWindow(fsm)

        # Verify stack has 2 pages
        self.assertEqual(window.stack.count(), 2)

        # Default page should be Page 0 (Aesthetic Voice HUD)
        self.assertEqual(window.stack.currentIndex(), 0)
        # Bottom debug panel must be hidden in Voice HUD!
        self.assertTrue(window.debug_panel.isHidden())

        # Toggle to Cockpit
        window.toggle_ui_mode()
        self.assertEqual(window.stack.currentIndex(), 1)
        # Bottom debug panel must be visible in Cockpit
        self.assertFalse(window.debug_panel.isHidden())

        # Toggle back to Voice HUD
        window.toggle_ui_mode()
        self.assertEqual(window.stack.currentIndex(), 0)
        self.assertTrue(window.debug_panel.isHidden())

        # Direct mode setting
        window.set_ui_mode(1)
        self.assertEqual(window.stack.currentIndex(), 1)
        self.assertFalse(window.debug_panel.isHidden())

        window.set_ui_mode(0)
        self.assertEqual(window.stack.currentIndex(), 0)
        self.assertTrue(window.debug_panel.isHidden())



if __name__ == "__main__":
    unittest.main()
