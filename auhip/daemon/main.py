import asyncio
import logging
import sys
import os

from auhip.core.config import config
from auhip.core.event_bus import event_bus
from auhip.core.service_manager import service_manager
from auhip.daemon.ipc_server import ipc_server

from auhip.audio.microphone import Microphone
from auhip.audio.snap_detector import SnapDetector
from auhip.audio.speech_recognition import SpeechRecognizer
from auhip.audio.tts import TextToSpeech
from auhip.core.state_machine import AuhipStateMachine
from auhip.core.agent import AuhipAgent
from auhip.vision.worker import VisionWorker

# Set matplotlib backend to Agg to prevent hangs during mediapipe import if accidentally imported early
os.environ['MPLBACKEND'] = 'Agg'
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="google.protobuf.symbol_database")

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger("auhip.daemon")

async def audio_loop(mic: Microphone, snap_detector: SnapDetector):
    """Continuously processes audio chunks for snap detection in the background."""
    try:
        while True:
            chunk = mic.get_audio_chunk()
            if chunk is not None:
                await snap_detector.process_audio(chunk)
            await asyncio.sleep(0.01)
    except asyncio.CancelledError:
        logger.info("Daemon audio loop stopped.")

async def main():
    logger.info("Starting AUHIP OS Daemon...")

    # Start foundational services
    event_bus.start()
    await ipc_server.start()
    service_manager.start_monitor()

    # Hardware & State Initialization
    mic = Microphone()
    snap_detector = SnapDetector()
    speech_recognizer = SpeechRecognizer()
    tts = TextToSpeech()
    
    agent = AuhipAgent()
    fsm = AuhipStateMachine(speech_recognizer, agent, mic, snap_detector, tts=tts)

    # Initialize speech recognition model asynchronously in a thread to prevent blocking
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, speech_recognizer.initialize)

    # Start audio hardware
    mic.start()
    snap_detector.start()
    await fsm.start()

    logger.info("AUHIP OS Daemon is now actively listening in the background.")

    # Run the continuous audio processing loop
    try:
        await audio_loop(mic, snap_detector)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.exception(f"Unexpected error in daemon main loop: {e}")
    finally:
        await fsm.stop()
        snap_detector.stop()
        mic.stop()
        tts.stop()
        await ipc_server.stop()
        await event_bus.stop()
        await service_manager.stop_monitor()
        logger.info("AUHIP OS Daemon shut down.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Daemon interrupted via keyboard.")
