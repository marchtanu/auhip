"""
WhisperRecognizer — Next-Generation faster-whisper Speech-to-Text Engine for AUHIP.

Key Architectural Enhancements:
  - English-specialized model support ('base.en', 'small.en', 'distil-small.en', 'turbo')
  - Domain vocabulary prompt biasing ('initial_prompt') for zero-error wake and command decoding
  - Anti-hallucination guards (condition_on_previous_text=False, repetition_penalty=1.15)
  - Dual-tier VAD: Fast energy pre-filtering + Neural Silero VAD segmentation
  - Non-blocking live model switching
"""

import asyncio
import logging
import queue
import time
import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_INITIAL_PROMPT = (
    "AUHIP executive assistant. Voice commands: daddy home, goodbye jojo, open camera, "
    "control mode, air mouse, cockpit, workspace, analyze my project, view directory tree, "
    "search codebase, list tasks, add task, complete task, stock, weather, YouTube Music."
)


class WhisperRecognizer:
    """
    Faster-Whisper based recognizer using shared Microphone stream.
    Records audio chunks, detects speech end via energy VAD,
    and transcribes the collected buffer instantly.
    """

    # ── VAD tunables ─────────────────────────────────────────────────────────
    SPEECH_START_THRESHOLD  = 0.014   # RMS energy to consider "speech started"
    SPEECH_END_THRESHOLD    = 0.007   # RMS energy to consider "speech ended"
    SPEECH_END_FRAMES       = 18      # Consecutive silent frames to mark phrase complete (~0.9s)
    MIN_SPEECH_FRAMES       = 5       # Min frames before we consider it a real phrase
    MAX_SILENCE_BEFORE_SEC  = 5.0     # Give up if user hasn't started speaking after this

    def __init__(
        self,
        model,
        sample_rate: int = 16000,
        initial_prompt: str = DEFAULT_INITIAL_PROMPT,
    ):
        """
        Args:
            model: A loaded faster_whisper.WhisperModel instance
            sample_rate: Audio sample rate in Hz (must match Microphone stream, typically 16000)
            initial_prompt: Vocabulary biasing prompt for decoder
        """
        self._model = model
        self._sample_rate = sample_rate
        self.initial_prompt = initial_prompt
        self.last_latency_ms = 0.0

    def set_model(self, model):
        """Hot-swap underlying Faster-Whisper model."""
        self._model = model
        logger.info("WhisperRecognizer model updated.")

    def _vad_record(
        self,
        mic,
        timeout: float,
        cancel_event: asyncio.Event | None,
    ) -> np.ndarray | None:
        """
        Records audio from shared mic queue using energy-based VAD.
        Returns a float32 numpy array of the captured speech, or None.
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
                    # Pre-speech buffering
                    pre_speech_buffer.append(chunk)
                    if len(pre_speech_buffer) > pre_roll_len:
                        pre_speech_buffer.pop(0)

                    if energy > self.SPEECH_START_THRESHOLD:
                        speech_started = True
                        logger.debug(f"Speech detected (energy={energy:.4f})")
                        speech_buffer = list(pre_speech_buffer)
                        speech_buffer.append(chunk)
                        silent_frame_count = 0
                    else:
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

                    # Silence threshold reached
                    if silent_frame_count >= self.SPEECH_END_FRAMES:
                        if len(speech_buffer) >= self.MIN_SPEECH_FRAMES:
                            logger.debug(
                                f"Speech end detected after {len(speech_buffer)} frames, "
                                f"{silent_frame_count} silent frames."
                            )
                            break
                        else:
                            # Noise burst discard
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
        Applies vocabulary prompt biasing and anti-hallucination guards.
        """
        if audio is None or len(audio) == 0:
            return ""

        try:
            # Normalize float32 buffer
            max_val = np.max(np.abs(audio))
            if max_val > 0:
                audio = audio / max_val

            # Execute transcription with Silero VAD filtering and prompt biasing
            segments, info = self._model.transcribe(
                audio,
                language="en",
                beam_size=3,
                best_of=3,
                condition_on_previous_text=False,  # Prevent repetition loops
                repetition_penalty=1.15,          # Penalize duplicate words
                no_speech_threshold=0.6,          # Reject dead silence
                compression_ratio_threshold=2.4,  # Reject hallucination loops
                initial_prompt=self.initial_prompt, # Domain keyword bias
                vad_filter=True,                  # Built-in Silero VAD
                vad_parameters=dict(
                    min_silence_duration_ms=350,
                    speech_pad_ms=120,
                ),
            )

            text = " ".join(seg.text.strip() for seg in segments).strip().lower()
            logger.info(f"Whisper transcribed: '{text}' (lang={info.language}, prob={info.language_probability:.2f})")
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
        self.last_latency_ms = (time.time() - t0) * 1000
        logger.debug(f"Whisper transcription took {self.last_latency_ms:.0f}ms")

        return text if text else None
