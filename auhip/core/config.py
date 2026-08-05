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

    # faster-whisper model size: "tiny" (~0.3s), "base" (~0.5s), "small" (~0.8s), "medium" (~1.5s)
    WHISPER_MODEL_SIZE: str = "base"
    # Compute device: "cpu" always works; "cuda" requires NVIDIA GPU + cuDNN
    WHISPER_DEVICE: str = "cpu"
    # int8 quantisation — much faster on CPU with minimal accuracy loss
    WHISPER_COMPUTE_TYPE: str = "int8"

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

config = Config()
