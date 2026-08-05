"""
WhisperRecognizer — faster-whisper based speech-to-text engine for auhip.

Architecture:
  - Records via the shared Microphone queue (float32 chunks)
  - Uses a lightweight Voice Activity Detector (VAD) to detect speech start/end
  - Transcribes with faster-whisper (local, fully offline)
  - Returns text in ~0.3–0.8s after the user stops speaking

Model size tradeoffs (set WHISPER_MODEL_SIZE in config.py):
  "tiny"   → ~39 MB,  ~0.3s, good accuracy
  "base"   → ~74 MB,  ~0.5s, great accuracy  ← recommended default
  "small"  → ~244 MB, ~0.8s, excellent accuracy
  "medium" → ~769 MB, ~1.5s, near-perfect accuracy (needs more RAM)
"""

import asyncio
import logging
import queue
import time
import numpy as np

logger = logging.getLogger(__name__)


class WhisperRecognizer:
    """
    Faster-Whisper based recognizer using shared Microphone stream.
    Records audio chunks, detects speech end via energy VAD,
    and transcribes the collected buffer instantly.
    """

    # ── VAD tunables ─────────────────────────────────────────────────────────
    SPEECH_START_THRESHOLD  = 0.015   # RMS energy to consider "speech started"
    SPEECH_END_THRESHOLD    = 0.008   # RMS energy to consider "speech ended"
    SPEECH_END_FRAMES       = 20      # How many consecutive silent frames end a phrase
    MIN_SPEECH_FRAMES       = 5       # Min frames before we consider it a real phrase
    MAX_SILENCE_BEFORE_SEC  = 5.0     # Give up if user hasn't started speaking after this

    def __init__(self, model, sample_rate: int = 16000):
        """
        Args:
            model: A loaded faster_whisper.WhisperModel instance (shared)
            sample_rate: Audio sample rate in Hz (must match Microphone stream)
        """
        self._model = model
        self._sample_rate = sample_rate

    def _vad_record(
        self,
        mic,
        timeout: float,
        cancel_event: asyncio.Event | None,
    ) -> np.ndarray | None:
        """
        Records audio from shared mic queue using energy-based VAD.
        Returns a float32 numpy array of the captured speech, or None.

        Flow:
          1. Wait for speech to start (energy > SPEECH_START_THRESHOLD)
          2. Accumulate audio frames
          3. Stop after SPEECH_END_FRAMES consecutive silent frames
          4. Return everything from speech-start to speech-end
        """
        q = mic.subscribe()
        try:
            pre_speech_buffer = []   # Rolling buffer before speech starts (for consonants)
            speech_buffer = []
            silent_frame_count = 0
            speech_started = False
            pre_roll_len = 8         # Keep ~0.2s of pre-speech audio

            start_time = time.time()
            elapsed = 0.0

            while elapsed < timeout:
                if cancel_event and cancel_event.is_set():
                    logger.debug("WhisperRecognizer: Cancelled by event.")
                    return None

                try:
                    chunk = q.get(timeout=0.05)  # 50ms polling
                except queue.Empty:
                    elapsed = time.time() - start_time
                    continue

                # Flatten to 1D float32
                if chunk.ndim > 1:
                    chunk = chunk[:, 0]
                chunk = chunk.astype(np.float32)

                energy = float(np.sqrt(np.mean(chunk ** 2)))
                elapsed = time.time() - start_time

                if not speech_started:
                    # Check for speech start
                    pre_speech_buffer.append(chunk)
                    if len(pre_speech_buffer) > pre_roll_len:
                        pre_speech_buffer.pop(0)

                    if energy > self.SPEECH_START_THRESHOLD:
                        speech_started = True
                        logger.debug(f"Speech detected (energy={energy:.4f})")
                        # Include pre-speech buffer so we don't miss leading consonants
                        speech_buffer = list(pre_speech_buffer)
                        speech_buffer.append(chunk)
                        silent_frame_count = 0
                    else:
                        # Haven't heard speech yet — check max silence timeout
                        if elapsed > self.MAX_SILENCE_BEFORE_SEC:
                            logger.debug("No speech detected within pre-speech timeout.")
                            return None
                else:
                    # Speech in progress — accumulate
                    speech_buffer.append(chunk)

                    if energy < self.SPEECH_END_THRESHOLD:
                        silent_frame_count += 1
                    else:
                        silent_frame_count = 0

                    # Enough silence after speech → phrase complete
                    if silent_frame_count >= self.SPEECH_END_FRAMES:
                        if len(speech_buffer) >= self.MIN_SPEECH_FRAMES:
                            logger.debug(
                                f"Speech end detected after {len(speech_buffer)} frames, "
                                f"{silent_frame_count} silent frames."
                            )
                            break
                        else:
                            # Too short — probably a noise burst; reset
                            logger.debug("Speech burst too short, ignoring.")
                            speech_buffer.clear()
                            speech_started = False
                            silent_frame_count = 0

            if not speech_buffer:
                return None

            return np.concatenate(speech_buffer)

        finally:
            mic.unsubscribe(q)

    def _transcribe(self, audio: np.ndarray) -> str:
        """
        Transcribe a float32 audio array using faster-whisper.
        Returns lowercased text, or empty string.
        """
        if audio is None or len(audio) == 0:
            return ""

        try:
            # faster-whisper expects float32, range [-1, 1], at model's sample rate
            # Normalise in case of clipping
            max_val = np.max(np.abs(audio))
            if max_val > 0:
                audio = audio / max_val

            segments, info = self._model.transcribe(
                audio,
                language="en",
                beam_size=3,           # lower = faster, higher = more accurate
                vad_filter=True,       # built-in VAD removes silence within the clip
                vad_parameters=dict(
                    min_silence_duration_ms=300,
                    speech_pad_ms=100,
                ),
            )

            text = " ".join(seg.text.strip() for seg in segments).strip().lower()
            logger.info(f"Whisper transcribed: '{text}'")
            return text

        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            return ""

    def listen(
        self,
        mic,
        timeout: float = 10.0,
        cancel_event: asyncio.Event | None = None,
    ) -> str | None:
        """
        Blocking call: records speech from mic queue, transcribes, returns text.
        Returns None if no speech detected or cancelled.
        """
        audio = self._vad_record(mic, timeout, cancel_event)
        if audio is None:
            return None

        t0 = time.time()
        text = self._transcribe(audio)
        logger.debug(f"Transcription took {(time.time() - t0)*1000:.0f}ms")

        return text if text else None
