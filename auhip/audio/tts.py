"""
auhip Text-to-Speech (TTS) Engine.

Dual-engine architecture:
  1. Primary:  edge-tts  — High-fidelity neural voice synthesis (Jarvis British, US male/female)
  2. Fallback: pyttsx3   — 100% offline Windows SAPI5 speech synthesis

Features:
  - In-memory MP3 streaming and PyAV PCM decoding (zero temp files on disk)
  - Non-blocking async playback with instant cancellation / interrupt support
  - Text sanitization (removes markdown, code blocks, URLs, and emojis)
  - Echo suppression coordination (tracks is_speaking state and fires event_bus events)
"""

import asyncio
import io
import logging
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import numpy as np
import sounddevice as sd

from auhip.core.config import config
from auhip.core.event_bus import event_bus

logger = logging.getLogger(__name__)

# Optional dependencies
try:
    import edge_tts
    _HAS_EDGE_TTS = True
except ImportError:
    edge_tts = None
    _HAS_EDGE_TTS = False

try:
    import av
    _HAS_AV = True
except ImportError:
    av = None
    _HAS_AV = False

try:
    import pyttsx3
    _HAS_PYTTSX3 = True
except ImportError:
    pyttsx3 = None
    _HAS_PYTTSX3 = False

_thread_local = threading.local()


def clean_text_for_speech(text: str, max_chars: int = 450) -> str:
    """
    Sanitizes raw response text (which may contain markdown, code, URLs, or emojis)
    into clean, natural conversational text suitable for speech synthesis.
    """
    if not text:
        return ""

    s = text.strip()

    # 1. Replace multiline code blocks (```...```) with a brief spoken placeholder
    s = re.sub(r"```[\w]*\n[\s\S]*?\n```", " Here is the code snippet. ", s)
    s = re.sub(r"```[\s\S]*?```", " Here is the code snippet. ", s)

    # 2. Replace inline code `code` with code
    s = re.sub(r"`([^`]+)`", r"\1", s)

    # 3. Replace markdown links [label](url) with label
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)

    # 4. Remove raw URLs
    s = re.sub(r"https?://\S+", "link", s)

    # 5. Remove HTML tags
    s = re.sub(r"<[^>]+>", " ", s)

    # 6. Remove markdown formatting characters (*, _, ~, #, >, - at line starts)
    s = re.sub(r"[*_~#]+", "", s)
    s = re.sub(r"^[\s]*[-*+]\s+", "", s, flags=re.MULTILINE)
    s = re.sub(r"^[\s]*\d+\.\s+", "", s, flags=re.MULTILINE)

    # 7. Remove emojis, variation selectors, and non-standard unicode symbols
    emoji_pattern = re.compile(
        "["
        "\U00010000-\U0010ffff"
        "\u2600-\u27bf"
        "\u2300-\u23ff"
        "\u2b50-\u2b55"
        "\u3030"
        "\ufe00-\ufe0f"
        "\u200d"
        "]+",
        flags=re.UNICODE
    )
    s = emoji_pattern.sub("", s)


    # 8. Expand common symbols to spoken words
    s = re.sub(r"°\s*C\b", " degrees Celsius", s)
    s = re.sub(r"°\s*F\b", " degrees Fahrenheit", s)
    s = s.replace("°", " degrees ")
    s = s.replace("%", " percent ")
    s = s.replace("&", " and ")

    # 9. Clean up bullet dashes, pipes, and excessive punctuation
    s = s.replace("|", " ").replace("---", " ").replace("==", " ")
    s = re.sub(r"\s+", " ", s).strip()


    # 9. Length protection: Truncate at sentence boundary if too long
    if len(s) > max_chars:
        # Find last sentence end before max_chars
        cutoff = s[:max_chars]
        last_period = max(cutoff.rfind(". "), cutoff.rfind("! "), cutoff.rfind("? "))
        if last_period > int(max_chars * 0.5):
            s = cutoff[:last_period + 1] + " And more."
        else:
            s = cutoff.rstrip() + "..."

    return s


class TextToSpeech:
    """
    Asynchronous Text-to-Speech manager.
    Coordinates speech generation, audio playback, cancellation, and mute state.
    """

    def __init__(
        self,
        engine: Optional[str] = None,
        voice: Optional[str] = None,
        enabled: Optional[bool] = None,
    ):
        self.enabled = enabled if enabled is not None else getattr(config, "TTS_ENABLED", True)
        self.engine = engine or getattr(config, "TTS_ENGINE", "edge")
        self.voice = voice or getattr(config, "TTS_VOICE", "en-GB-RyanNeural")
        self.rate = getattr(config, "TTS_RATE", "+0%")
        self.pitch = getattr(config, "TTS_PITCH", "+0Hz")
        self.volume = getattr(config, "TTS_VOLUME", "+0%")
        self.max_chars = getattr(config, "TTS_MAX_CHARS", 450)

        self._is_speaking = False
        self._state_lock = threading.Lock()
        self._is_muted = not self.enabled

        self._cancel_event = threading.Event()
        self._current_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="auhip_tts")

        # pyttsx3 offline engine instance (lazy loaded)
        self._pyttsx3_engine = None

        logger.info(
            f"TTS initialized. Engine: '{self.engine}', Voice: '{self.voice}', Muted: {self._is_muted}"
        )

    def _set_speaking(self, val: bool):
        with self._state_lock:
            self._is_speaking = val

    @property
    def is_speaking(self) -> bool:
        """Returns True if audio is actively playing."""
        with self._state_lock:
            return self._is_speaking

    @property
    def is_muted(self) -> bool:
        """Returns True if TTS is muted or disabled."""
        return self._is_muted

    def set_muted(self, muted: bool):
        """Mute or unmute speech output."""
        self._is_muted = muted
        if muted:
            self.stop()
        logger.info(f"TTS muted state changed: {self._is_muted}")

    def set_voice(self, voice_name: str):
        """Change the active voice."""
        self.voice = voice_name
        logger.info(f"TTS voice updated to: {voice_name}")

    def set_engine(self, engine: str):
        """Switch between 'edge' and 'pyttsx3'."""
        if engine in ("edge", "pyttsx3"):
            self.engine = engine
            logger.info(f"TTS engine updated to: {engine}")

    def barge_in(self) -> bool:
        """
        Triggered when user starts speaking or requests an interruption.
        Immediately stops playback and returns True if speech was actively cut off.
        """
        if self.is_speaking:
            logger.info("Barge-in: User voice detected. Cutting off TTS playback immediately.")
            self.stop()
            return True
        return False

    def stop(self):
        """Immediately stop speaking and abort current playback."""
        self._cancel_event.set()
        try:
            sd.stop()
        except Exception as e:
            logger.debug(f"sounddevice stop exception: {e}")

        if self._current_task and not self._current_task.done():
            self._current_task.cancel()

        self._set_speaking(False)
        logger.debug("TTS playback stopped by request.")

    # ── Speech Execution ──────────────────────────────────────────────────────

    async def speak(self, text: str, block: bool = True) -> bool:
        """
        Synthesizes and speaks text.
        If block=True, awaits completion of audio playback.
        Returns True if speech was executed, False if skipped/cancelled.
        """
        if self._is_muted or not text:
            return False

        clean_text = clean_text_for_speech(text, self.max_chars)
        if not clean_text:
            return False

        async with self._lock:
            # Stop any currently running speech before starting new one
            self.stop()
            self._cancel_event.clear()

            self._set_speaking(True)
            await event_bus.publish("TTS_STARTED", {
                "text": text,
                "clean_text": clean_text,
                "voice": self.voice,
            })

            success = False
            try:
                # 1. Try edge-tts if selected and available
                if self.engine == "edge" and _HAS_EDGE_TTS and _HAS_AV:
                    try:
                        success = await self._speak_edge(clean_text)
                    except Exception as e:
                        logger.warning(f"Edge TTS failed ({e}), falling back to pyttsx3.")
                        success = await self._speak_pyttsx3(clean_text)
                else:
                    # 2. Use offline pyttsx3
                    success = await self._speak_pyttsx3(clean_text)
            except asyncio.CancelledError:
                logger.debug("TTS task was cancelled.")
                success = False
            except Exception as e:
                logger.exception(f"Unexpected error in TTS: {e}")
                success = False
            finally:
                self._set_speaking(False)
                await event_bus.publish("TTS_FINISHED", {
                    "text": text,
                    "success": success,
                })

            return success

    # ── Edge-TTS Engine ───────────────────────────────────────────────────────

    async def _speak_edge(self, text: str) -> bool:
        """Synthesizes using Microsoft Edge Neural TTS and plays in-memory with sounddevice."""
        logger.debug(f"Edge-TTS synthesizing: '{text[:60]}...'")

        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice,
            rate=self.rate,
            pitch=self.pitch,
            volume=self.volume,
        )

        mp3_buffer = bytearray()
        async for chunk in communicate.stream():
            if self._cancel_event.is_set():
                return False
            if chunk["type"] == "audio":
                mp3_buffer.extend(chunk["data"])

        if not mp3_buffer or self._cancel_event.is_set():
            return False

        # Decode MP3 bytes in memory using PyAV (run in executor to keep loop responsive)
        loop = asyncio.get_running_loop()
        audio_array, sample_rate = await loop.run_in_executor(
            self._executor, self._decode_mp3_to_pcm, bytes(mp3_buffer)
        )

        if audio_array is None or self._cancel_event.is_set():
            return False

        # Play audio via sounddevice non-blocking
        duration = len(audio_array) / sample_rate
        sd.play(audio_array, samplerate=sample_rate)

        # Wait until playback finishes or cancel is requested
        start_time = loop.time()
        while loop.time() - start_time < duration:
            if self._cancel_event.is_set():
                sd.stop()
                return False
            await asyncio.sleep(0.02)

        sd.stop()
        return True


    def _decode_mp3_to_pcm(self, mp3_bytes: bytes):
        """Decode in-memory MP3 bytes into a normalized float32 numpy array for sounddevice."""
        try:
            container = av.open(io.BytesIO(mp3_bytes))
            stream = container.streams.audio[0]
            sample_rate = stream.rate

            frames = []
            for frame in container.decode(stream):
                frames.append(frame.to_ndarray())
            container.close()

            if not frames:
                return None, sample_rate

            audio = np.concatenate(frames, axis=1)

            # Convert to float32 normalized [-1.0, 1.0]
            if audio.dtype == np.int16:
                audio = audio.astype(np.float32) / 32768.0
            elif audio.dtype == np.int32:
                audio = audio.astype(np.float32) / 2147483648.0
            elif audio.dtype != np.float32:
                audio = audio.astype(np.float32)

            # Transpose (channels, samples) -> (samples, channels)
            if audio.ndim == 2:
                audio = audio.T

            return audio, sample_rate
        except Exception as e:
            logger.error(f"Failed to decode MP3 stream: {e}")
            return None, 24000

    # ── Offline pyttsx3 Engine ────────────────────────────────────────────────

    async def _speak_pyttsx3(self, text: str) -> bool:
        """Speaks using offline Windows SAPI5 via pyttsx3."""
        if not _HAS_PYTTSX3:
            logger.error("pyttsx3 is not installed. Offline TTS unavailable.")
            return False

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self._run_pyttsx3_blocking, text)

    def _run_pyttsx3_blocking(self, text: str) -> bool:
        """Worker thread function for pyttsx3 to avoid blocking Qt loop."""
        try:
            # Lazy initialize COM SAPI5 engine per worker thread
            if not hasattr(_thread_local, "engine") or _thread_local.engine is None:
                _thread_local.engine = pyttsx3.init()

            engine = _thread_local.engine
            rate = getattr(config, "TTS_PYTTSX3_RATE", 180)
            engine.setProperty("rate", rate)

            voices = engine.getProperty("voices")
            idx = getattr(config, "TTS_PYTTSX3_VOICE_INDEX", 0)
            if voices and 0 <= idx < len(voices):
                engine.setProperty("voice", voices[idx].id)

            engine.say(text)
            engine.runAndWait()
            return True
        except Exception as e:
            logger.error(f"pyttsx3 execution error: {e}")
            _thread_local.engine = None
            return False
