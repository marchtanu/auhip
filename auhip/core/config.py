import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    # Audio
    SAMPLERATE: int = 16000          # 16kHz — native rate for Vosk AND Whisper models
    CHANNELS: int = 1
    BLOCK_SIZE: int = 1600           # 100ms chunks at 16kHz
    MIC_DEVICE_INDEX: int | None = None

    # Snap Detection
    SNAP_THRESHOLD_MULTIPLIER: float = 6.0
    SNAP_REFRACTORY_PERIOD: float = 0.3
    SNAP_WINDOW_TIMEOUT: float = 2.0

    # Activation Phrases
    WAKE_PHRASE: str = "daddy home"
    SHUTDOWN_PHRASE: str = "goodbye jojo"
    GOODNIGHT_PHRASE: str = "goodnight"
    EXIT_PHRASE: str = "exit"

    # Speech Recognition Engine
    # Options: "whisper" (recommended), "vosk" (offline fallback), "google" (cloud)
    STT_ENGINE: str = "whisper"

    # faster-whisper model: "base.en" (recommended, ~0.35s), "small.en", "distil-small.en", "turbo", "base"
    WHISPER_MODEL_SIZE: str = os.getenv("WHISPER_MODEL_SIZE", "base.en")
    # Compute device: "cpu" (standard), "cuda" (GPU with cuDNN)
    WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "cpu")
    # Compute type: "int8" (optimal for CPU), "float16" (optimal for CUDA)
    WHISPER_COMPUTE_TYPE: str = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

    VOSK_MODEL_PATH: str = "vosk-model-small-en-us-0.15"
    WAKE_WORD_TIMEOUT: float = 8.0
    COMMAND_TIMEOUT: float = 10.0

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "auhip.log"

    # Sound Monitoring
    SOUND_DETECTION_THRESHOLD: float = 0.01

    # Weather (used by get_weather skill)
    # Leave blank to auto-detect city from IP via wttr.in
    WEATHER_CITY: str = ""

    # Timer notification chime
    # Set True to print a distinct separator in the response on timer completion
    TIMER_CHIME: bool = True

    # Text-to-Speech (TTS) Voice Synthesis
    TTS_ENABLED: bool = True
    # Primary engine: "edge" (natural neural voices) or "pyttsx3" (offline SAPI5)
    TTS_ENGINE: str = "edge"
    # Edge-TTS voice (e.g. "en-GB-RyanNeural" for British Jarvis, "en-US-ChristopherNeural" for US male, "en-US-AriaNeural" for US female)
    TTS_VOICE: str = "en-GB-RyanNeural"
    TTS_RATE: str = "+0%"
    TTS_PITCH: str = "+0Hz"
    TTS_VOLUME: str = "+0%"
    # Maximum characters to speak at once to avoid overly verbose monologues
    TTS_MAX_CHARS: int = 450
    # pyttsx3 offline fallback settings
    TTS_PYTTSX3_RATE: int = 180
    TTS_PYTTSX3_VOICE_INDEX: int = 0

    # Conversational Flow & Barge-In (OpenAI Voice Mode style)
    BARGE_IN_ENABLED: bool = True
    # If False (default), AUHIP remains in continuous Voice Mode without auto-reverting to Standby
    AUTO_STANDBY_ENABLED: bool = False
    CONVERSATION_TIMEOUT_SECONDS: float = 15.0  # Inactivity seconds before Standby (only if AUTO_STANDBY_ENABLED=True)

    # Hardware Optimization
    CAMERA_ON_DEMAND: bool = True  # Only activate camera & MediaPipe when in gesture/camera mode

config = Config()

