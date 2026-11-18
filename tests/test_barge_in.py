import os
import sys
import unittest
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from auhip.core.config import config
from auhip.audio.tts import TextToSpeech
from auhip.vision.worker import VisionWorker


class TestBargeInAndOptimization(unittest.TestCase):
    def setUp(self):
        self.tts = TextToSpeech(engine="edge", voice="en-GB-RyanNeural")

    def test_config_defaults(self):
        self.assertTrue(hasattr(config, "BARGE_IN_ENABLED"))
        self.assertTrue(config.BARGE_IN_ENABLED)
        self.assertTrue(hasattr(config, "CONVERSATION_TIMEOUT_SECONDS"))
        self.assertGreater(config.CONVERSATION_TIMEOUT_SECONDS, 0)
        self.assertTrue(hasattr(config, "CAMERA_ON_DEMAND"))
        self.assertTrue(config.CAMERA_ON_DEMAND)

    def test_barge_in_when_idle(self):
        self.assertFalse(self.tts.is_speaking)
        result = self.tts.barge_in()
        self.assertFalse(result)

    def test_barge_in_when_speaking(self):
        # Artificially set speaking flag
        self.tts._is_speaking = True
        result = self.tts.barge_in()
        self.assertTrue(result)
        self.assertFalse(self.tts.is_speaking)
        self.assertTrue(self.tts._cancel_event.is_set())

    def test_camera_on_demand_gating(self):
        worker = VisionWorker(fps=30)
        # In NONE mode with CAMERA_ON_DEMAND=True, camera must not run
        worker._on_set_vision_mode({"mode": "none"})
        self.assertFalse(worker.running)
        self.assertIsNone(worker.hand_tracker)

        # In SLEEP mode, low-power throttled camera (~7 FPS / 140ms) runs for emergency gesture
        worker._on_set_vision_mode({"mode": "sleep"})
        self.assertTrue(worker.running)
        self.assertEqual(worker.interval_ms, 140)
        worker.stop()


if __name__ == "__main__":
    unittest.main()
