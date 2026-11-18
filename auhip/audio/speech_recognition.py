"""
Hybrid Speech Recognition — three-tier engine stack:

  Tier 1 (primary):  faster-whisper   — local, fast (~0.5s), flexible vocabulary
  Tier 2 (fallback): Vosk             — local, instant, grammar-lockable
  Tier 3 (last):     Google Cloud     — cloud, slowest, most accurate

Engine is controlled by config.STT_ENGINE ("whisper" | "vosk" | "google").
"""

import logging
import asyncio
import json
import time
import queue
import os
import numpy as np

try:
    import vosk
except ImportError:
    vosk = None

try:
    from faster_whisper import WhisperModel as _WhisperModel
    _HAS_WHISPER = True
except ImportError:
    _HAS_WHISPER = False

import speech_recognition as sr
from ..core.config import config
from ..core.event_bus import event_bus

logger = logging.getLogger(__name__)


class SpeechRecognizer:
    """
    Three-tier hybrid speech recogniser.
    Primary: faster-whisper (STT_ENGINE="whisper")
    Fallback: Vosk offline  (STT_ENGINE="vosk")
    Last:     Google Cloud  (STT_ENGINE="google")
    """

    def __init__(self):
        self.recognizer = sr.Recognizer()
        self._vosk_model = None
        self._vosk_rec   = None
        self._whisper_model = None
        self._whisper_rec   = None   # WhisperRecognizer wrapper
        self._active_engine = config.STT_ENGINE  # "whisper" | "vosk" | "google"

    # ── Initialisation ────────────────────────────────────────────────────────

    def initialize(self) -> bool:
        """Load the configured primary engine. Falls back down the stack on failure."""
        if self._active_engine == "whisper":
            if self._init_whisper():
                logger.info("Speech engine: faster-whisper [OK]")
                return True
            logger.warning("Whisper unavailable — falling back to Vosk.")
            self._active_engine = "vosk"

        if self._active_engine == "vosk":
            if self._init_vosk():
                logger.info("Speech engine: Vosk [OK]")
                return True
            logger.warning("Vosk unavailable — falling back to Google Cloud.")
            self._active_engine = "google"

        logger.info("Speech engine: Google Cloud STT")
        return True  # Google always available (needs internet)

    def _notify_stt_status(self, data: dict):
        """Safely dispatch STT_STATUS updates across threads."""
        try:
            if hasattr(event_bus, "publish_sync"):
                event_bus.publish_sync("STT_STATUS", data)
        except Exception as e:
            logger.debug(f"Could not dispatch STT_STATUS: {e}")

    def _init_whisper(self) -> bool:
        """Initialize faster-whisper model (blocking — run in thread)."""
        if not _HAS_WHISPER:
            logger.error("faster-whisper not installed. Run: pip install faster-whisper")
            return False

        try:
            logger.info(
                f"Loading faster-whisper model '{config.WHISPER_MODEL_SIZE}' "
                f"on {config.WHISPER_DEVICE} ({config.WHISPER_COMPUTE_TYPE})..."
            )
            self._notify_stt_status({
                "status": "loading",
                "engine": "whisper",
                "model": config.WHISPER_MODEL_SIZE,
                "message": f"Loading faster-whisper model '{config.WHISPER_MODEL_SIZE}'..."
            })
            # Model is downloaded to HuggingFace cache on first run (~74 MB for 'base')
            self._whisper_model = _WhisperModel(
                config.WHISPER_MODEL_SIZE,
                device=config.WHISPER_DEVICE,
                compute_type=config.WHISPER_COMPUTE_TYPE,
            )
            # Warm up the model with a silent buffer so first call isn't slow
            _silence = np.zeros(3200, dtype=np.float32)
            list(self._whisper_model.transcribe(_silence, language="en")[0])
            logger.info("faster-whisper ready.")
            self._notify_stt_status({
                "status": "ready",
                "engine": "whisper",
                "model": config.WHISPER_MODEL_SIZE,
                "message": "faster-whisper ready."
            })

            from .whisper_recognizer import WhisperRecognizer
            self._whisper_rec = WhisperRecognizer(
                self._whisper_model,
                sample_rate=config.SAMPLERATE,
            )
            return True
        except Exception as e:
            logger.error(f"faster-whisper init failed: {e}")
            self._notify_stt_status({
                "status": "error",
                "engine": "whisper",
                "error": str(e)
            })
            return False

    def switch_whisper_model(self, model_size: str) -> bool:
        """Switch or upgrade the Faster-Whisper model size at runtime."""
        if not _HAS_WHISPER:
            return False
        try:
            logger.info(f"Switching Whisper model to '{model_size}'...")
            new_model = _WhisperModel(
                model_size,
                device=config.WHISPER_DEVICE,
                compute_type=config.WHISPER_COMPUTE_TYPE,
            )
            # Warm up
            _silence = np.zeros(3200, dtype=np.float32)
            list(new_model.transcribe(_silence)[0])

            self._whisper_model = new_model
            config.WHISPER_MODEL_SIZE = model_size
            if self._whisper_rec:
                self._whisper_rec.set_model(new_model)
            else:
                from .whisper_recognizer import WhisperRecognizer
                self._whisper_rec = WhisperRecognizer(self._whisper_model, sample_rate=config.SAMPLERATE)
            logger.info(f"Successfully switched to Whisper model '{model_size}'.")
            return True
        except Exception as e:
            logger.error(f"Failed to switch Whisper model to '{model_size}': {e}")
            return False

    def _init_vosk(self) -> bool:
        if not vosk:
            logger.error("Vosk module not installed.")
            return False
        if not os.path.exists(config.VOSK_MODEL_PATH):
            logger.error(f"Vosk model not found at: {config.VOSK_MODEL_PATH}")
            return False
        try:
            vosk.SetLogLevel(-1)
            self._vosk_model = vosk.Model(config.VOSK_MODEL_PATH)
            self._vosk_rec   = vosk.KaldiRecognizer(self._vosk_model, config.SAMPLERATE)
            logger.info("Vosk ready.")
            return True
        except Exception as e:
            logger.error(f"Vosk init failed: {e}")
            return False

    # ── Public API ────────────────────────────────────────────────────────────

    async def listen_for_command(
        self,
        timeout: float = 10.0,
        phrase_time_limit: float = 10.0,
        grammar: list = None,
        validator: callable = None,
        cancel_event: asyncio.Event = None,
        mic=None,
    ) -> str | None:
        """
        Async entry point — runs blocking recognition in a thread executor.
        Returns lowercased text or None.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._listen_blocking(timeout, phrase_time_limit, grammar, cancel_event, mic),
        )

    def process_chunk(self, audio_data) -> str | None:
        """Streaming chunk processing for Vosk (legacy support)."""
        if self._active_engine == "vosk" and self._vosk_rec:
            if audio_data.dtype != np.int16:
                audio_data = (audio_data * 32767).astype(np.int16)
            if self._vosk_rec.AcceptWaveform(audio_data.tobytes()):
                result = json.loads(self._vosk_rec.Result())
                return result.get("text")
        return None

    # ── Engine dispatch ───────────────────────────────────────────────────────

    def _listen_blocking(
        self,
        timeout: float,
        phrase_time_limit: float,
        grammar: list,
        cancel_event: asyncio.Event,
        mic,
    ) -> str | None:
        engine = self._active_engine

        # Grammar locking only works with Vosk — fall back to Vosk for wake-word calls
        if grammar and engine == "whisper":
            engine = "vosk" if self._vosk_rec else "whisper"

        if engine == "whisper" and self._whisper_rec:
            return self._listen_whisper(timeout, cancel_event, mic)

        if engine == "vosk" and self._vosk_model:
            text, buf = self._listen_vosk(timeout, grammar, cancel_event, mic)
            if not text and buf:
                return self._google_from_buffer(buf)
            return text

        # Google-only fallback
        return self._listen_google(timeout, phrase_time_limit)

    # ── Whisper engine ────────────────────────────────────────────────────────

    def _listen_whisper(
        self,
        timeout: float,
        cancel_event: asyncio.Event,
        mic,
    ) -> str | None:
        """Record with VAD then transcribe via faster-whisper."""
        if not mic:
            logger.warning("Whisper needs a shared mic stream — falling back to Google.")
            return self._listen_google(timeout, timeout)

        return self._whisper_rec.listen(mic, timeout=timeout, cancel_event=cancel_event)

    # ── Vosk engine ──────────────────────────────────────────────────────────

    def _listen_vosk(
        self,
        timeout: float,
        grammar: list,
        cancel_event: asyncio.Event,
        mic,
    ) -> tuple[str | None, bytes | None]:
        import sounddevice as sd
        audio_buffer = bytearray()
        try:
            if grammar:
                grammar_json = json.dumps(grammar + ["[unk]"])
                rec = vosk.KaldiRecognizer(self._vosk_model, config.SAMPLERATE, grammar_json)
            else:
                rec = self._vosk_rec

            if mic:
                q = mic.subscribe()
                try:
                    start = time.time()
                    while time.time() - start < timeout:
                        if cancel_event and cancel_event.is_set():
                            break
                        try:
                            data = q.get(timeout=0.1)
                        except queue.Empty:
                            continue
                        if data.dtype != np.int16:
                            data = (data * 32767).astype(np.int16)
                        chunk_bytes = data.tobytes()
                        audio_buffer.extend(chunk_bytes)
                        if rec.AcceptWaveform(chunk_bytes):
                            result = json.loads(rec.Result())
                            text = result.get("text", "")
                            if text:
                                logger.info(f"Vosk: '{text}'")
                                return text, bytes(audio_buffer)
                finally:
                    mic.unsubscribe(q)
            else:
                with sd.RawInputStream(
                    samplerate=config.SAMPLERATE, blocksize=8000,
                    dtype='int16', channels=1, device=config.MIC_DEVICE_INDEX
                ) as stream:
                    start = time.time()
                    while time.time() - start < timeout:
                        if cancel_event and cancel_event.is_set():
                            break
                        data, _ = stream.read(4000)
                        audio_buffer.extend(data)
                        if rec.AcceptWaveform(bytes(data)):
                            result = json.loads(rec.Result())
                            text = result.get("text", "")
                            if text:
                                logger.info(f"Vosk: '{text}'")
                                return text, bytes(audio_buffer)

            result = json.loads(rec.FinalResult())
            text = result.get("text", "")
            if text:
                logger.info(f"Vosk (Final): '{text}'")
            return (text or None), bytes(audio_buffer)

        except Exception as e:
            logger.error(f"Vosk error: {e}")
        return None, bytes(audio_buffer)

    # ── Google Cloud engine ───────────────────────────────────────────────────

    def _google_from_buffer(self, buffer: bytes) -> str | None:
        try:
            logger.info("Google Cloud fallback recognition...")
            audio_data = sr.AudioData(buffer, config.SAMPLERATE, 2)
            text = self.recognizer.recognize_google(audio_data).lower()
            logger.info(f"Google: '{text}'")
            return text
        except sr.UnknownValueError:
            logger.debug("Google fallback: could not understand audio.")
        except Exception as e:
            logger.error(f"Google fallback error: {e}")
        return None

    def _listen_google(self, timeout: float, phrase_time_limit: float) -> str | None:
        try:
            with sr.Microphone(device_index=config.MIC_DEVICE_INDEX) as source:
                audio = self.recognizer.listen(
                    source, timeout=timeout, phrase_time_limit=phrase_time_limit
                )
            text = self.recognizer.recognize_google(audio).lower()
            logger.info(f"Google direct: '{text}'")
            return text
        except sr.WaitTimeoutError:
            logger.info("Google: listening timed out.")
        except sr.UnknownValueError:
            logger.warning("Google: could not understand audio.")
        except sr.RequestError as e:
            logger.error(f"Google API error: {e}")
        except Exception as e:
            logger.error(f"Google error: {e}")
        return None
