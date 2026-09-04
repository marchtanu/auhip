import os
import sys
import unittest

# Run Qt headlessly
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtWidgets import QApplication

from auhip.audio.tts import TextToSpeech
from auhip.gui.components.debug_panel import DebugPanel
from auhip.gui.components.left_panel import LeftPanel
from auhip.gui.components.center_panel import CenterPanel
from auhip.gui.main_window import AuhipMainWindow


class TestGuiTtsIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.tts = TextToSpeech(engine="edge", voice="en-GB-RyanNeural")

    def test_debug_panel_tts(self):
        panel = DebugPanel(fsm=None)
        panel.set_tts_instance(self.tts)

        # Verify initial states
        self.assertTrue(panel._tts_check.isChecked())
        self.assertFalse(self.tts.is_muted)

        # Toggle muted
        panel._tts_check.setChecked(False)
        self.assertTrue(self.tts.is_muted)

        panel._tts_check.setChecked(True)
        self.assertFalse(self.tts.is_muted)

        # Test voice combo box selection
        # Change to offline
        idx = panel.tts_voice_select.findData("offline")
        self.assertGreaterEqual(idx, 0)
        panel.tts_voice_select.setCurrentIndex(idx)
        self.assertEqual(self.tts.engine, "pyttsx3")

        # Change back to edge US Guy
        idx = panel.tts_voice_select.findData("en-US-GuyNeural")
        self.assertGreaterEqual(idx, 0)
        panel.tts_voice_select.setCurrentIndex(idx)
        self.assertEqual(self.tts.engine, "edge")
        self.assertEqual(self.tts.voice, "en-US-GuyNeural")

    def test_left_panel_tts_indicator(self):
        lp = LeftPanel()
        lp.set_tts_active(True, speaking=False)
        self.assertIn("Ready", lp.tts_lbl.text())

        lp.set_tts_active(True, speaking=True)
        self.assertIn("Speaking", lp.tts_lbl.text())

        lp.set_tts_active(False, speaking=False)
        self.assertIn("Muted", lp.tts_lbl.text())

    def test_center_panel_speaking(self):
        cp = CenterPanel()
        cp.set_speaking(True)
        self.assertIn("Speaking", cp.r_header.text())

        cp.set_speaking(False)
        self.assertEqual(cp.r_header.text(), "auhip response")


if __name__ == "__main__":
    unittest.main()
