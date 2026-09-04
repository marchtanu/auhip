import asyncio
import logging
import sys
import os

# Set matplotlib backend to Agg to prevent hangs during mediapipe import
os.environ['MPLBACKEND'] = 'Agg'

import warnings
# Silence Protobuf deprecation warning from Mediapipe
warnings.filterwarnings("ignore", category=UserWarning, module="google.protobuf.symbol_database")

from logging.handlers import RotatingFileHandler
import numpy as np

import qasync
from PyQt6.QtWidgets import QApplication

from auhip.core.config import config
from auhip.core.event_bus import event_bus
from auhip.audio.microphone import Microphone
from auhip.audio.snap_detector import SnapDetector
from auhip.audio.speech_recognition import SpeechRecognizer
from auhip.audio.tts import TextToSpeech
from auhip.core.state_machine import AuhipStateMachine
from auhip.core.agent import AuhipAgent
from auhip.gui.main_window import AuhipMainWindow
from auhip.vision.worker import VisionWorker

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        RotatingFileHandler(config.LOG_FILE, maxBytes=5_000_000, backupCount=3, encoding="utf-8"),
    ],
)
logger = logging.getLogger("auhip")


async def audio_loop(mic: Microphone, snap_detector: SnapDetector,
                     window: AuhipMainWindow, debug_panel, tts: TextToSpeech = None):
    """Continuously processes audio chunks for snap detection, waveform, and barge-in interruption."""
    barge_in_streak = 0
    try:
        while True:
            if debug_panel.mic_enabled:
                chunk = mic.get_audio_chunk()
                if chunk is not None:
                    # 1. Snap Detection & Waveform UI Feed
                    await snap_detector.process_audio(chunk)
                    window.feed_audio(chunk)

                    # 2. Instant Barge-In Detection (OpenAI Voice Mode style)
                    if tts and tts.is_speaking and getattr(config, "BARGE_IN_ENABLED", True):
                        try:
                            sample = chunk[:, 0] if chunk.ndim > 1 else chunk
                            energy = float(np.sqrt(np.mean(sample.astype(np.float32) ** 2)))
                            threshold = getattr(config, "SOUND_DETECTION_THRESHOLD", 0.01) * 3.5
                            if energy > threshold:
                                barge_in_streak += 1
                                if barge_in_streak >= 2:
                                    tts.barge_in()
                                    barge_in_streak = 0
                            else:
                                barge_in_streak = max(0, barge_in_streak - 1)
                        except Exception:
                            pass
                    else:
                        barge_in_streak = 0

            await asyncio.sleep(0.01)
    except (asyncio.CancelledError, RuntimeError):
        logger.info("Audio loop stopped.")


async def main(mode="direct"):
    logger.info(f"Starting auhip Assistant in '{mode.upper()}' mode...")

    # ── Initialize Components ─────────────────────────────────────────────
    mic = Microphone()
    snap_detector = SnapDetector()
    speech_recognizer = SpeechRecognizer()
    tts = TextToSpeech()

    agent = AuhipAgent()
    fsm = AuhipStateMachine(speech_recognizer, agent, mic, snap_detector, tts=tts)
    vision_worker = VisionWorker()

    # ── Build GUI ─────────────────────────────────────────────────────────
    hide_on_standby = (mode == "standby")
    window = AuhipMainWindow(fsm, mic, vision_worker, hide_on_standby=hide_on_standby, tts=tts)
    
    # ── 1. Calibrate & initialize speech engines non-blocking ──────────────
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, speech_recognizer.initialize)

    # ── 2. Start Event Bus & Audio Hardware ──────────────────────────────────
    event_bus.start()
    mic.start()
    snap_detector.start()

    # Connect mic to GUI for hardware switching
    window.debug_panel.set_mic_instance(mic)

    logger.info("auhip is ready.")
    logger.info(f"  Mode           : '{mode}'")
    logger.info(f"  Wake phrase    : '{config.WAKE_PHRASE}'")
    logger.info(f"  Shutdown phrase: '{config.SHUTDOWN_PHRASE}'")
    logger.info(f"  TTS Engine     : '{config.TTS_ENGINE}' (Voice: {config.TTS_VOICE})")
    logger.info(f"  Barge-In       : {getattr(config, 'BARGE_IN_ENABLED', True)}")

    # ── 3. Start State Machine ──────────────────────────────────────────────
    await fsm.start()

    # ── 4. Launch Mode Loop ──────────────────────────────────────────────────
    if mode == "direct":
        window.show()  # Display GUI window immediately on launch
        asyncio.create_task(fsm._enter_voice_mode())
    else:
        window.hide()  # Hidden background listener mode

    # ── 5. Run Audio Processing Loop ────────────────────────────────────────
    try:
        await audio_loop(mic, snap_detector, window, window.debug_panel, tts=tts)
    except asyncio.CancelledError:
        pass

    except Exception as e:
        logger.exception(f"Unexpected error in main loop: {e}")
    finally:
        await fsm.stop()
        await event_bus.stop()
        snap_detector.stop()
        mic.stop()
        tts.stop()
        vision_worker.stop()
        logger.info("auhip shut down.")





if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AUHIP Personal Assistant")
    parser.add_argument("--mode", choices=["direct", "standby"], default="direct",
                        help="Startup mode: 'direct' (GUI + auto-activate) or 'standby' (hidden background snap listener)")
    parser.add_argument("--direct", action="store_true", help="Method 1: Direct interactive GUI mode")
    parser.add_argument("--standby", action="store_true", help="Method 2: Standby snap/voice listener mode")
    
    args, unknown = parser.parse_known_args()
    selected_mode = "standby" if args.standby else ("direct" if args.direct else args.mode)

    app = QApplication(sys.argv)
    app.setApplicationName("auhip Assistant")

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    with loop:
        try:
            loop.run_until_complete(main(selected_mode))
        except (KeyboardInterrupt, RuntimeError):
            logger.info("auhip closed gracefully.")
        finally:
            if not loop.is_closed():
                loop.stop()

