import unittest
import os
import sys
import numpy as np

sys.path.insert(0, os.path.abspath("."))

from auhip.audio.speech_recognition import SpeechRecognizer
from auhip.audio.whisper_recognizer import WhisperRecognizer, DEFAULT_INITIAL_PROMPT
from auhip.core.config import config


class TestWhisperEngine(unittest.TestCase):

    def setUp(self):
        self.sr = SpeechRecognizer()
        self.initialized = self.sr.initialize()

    def test_whisper_initialization(self):
        self.assertTrue(self.initialized)
        self.assertIsNotNone(self.sr._whisper_model)
        self.assertIsNotNone(self.sr._whisper_rec)
        self.assertEqual(config.WHISPER_MODEL_SIZE, "base.en")

    def test_whisper_transcribe_empty_and_silence(self):
        # Empty array
        res_empty = self.sr._whisper_rec._transcribe(np.array([], dtype=np.float32))
        self.assertEqual(res_empty, "")

        # Silent buffer (1.5 seconds of silence at 16kHz)
        silence = np.zeros(24000, dtype=np.float32)
        res_silence = self.sr._whisper_rec._transcribe(silence)
        # Anti-hallucination guard should ensure silence produces empty string
        self.assertEqual(res_silence, "")

    def test_whisper_initial_prompt(self):
        self.assertIn("AUHIP", self.sr._whisper_rec.initial_prompt)
        self.assertIn("daddy home", self.sr._whisper_rec.initial_prompt)
        self.assertIn("air mouse", self.sr._whisper_rec.initial_prompt)

    def test_switch_whisper_model(self):
        # Test switching to base or re-setting base.en
        success = self.sr.switch_whisper_model("base.en")
        self.assertTrue(success)
        self.assertEqual(config.WHISPER_MODEL_SIZE, "base.en")


if __name__ == "__main__":
    unittest.main()
