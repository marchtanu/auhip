\
# Speech Recognition System

auhip features a hybrid speech recognition architecture that allows for both high-speed local processing and high-accuracy cloud processing. It operates as a 3-tier system:

## 1. Recognition Engines (3-Tier Stack)

### Tier 1 (Primary): faster-whisper
- **Model:** Local whisper model (`base` by default, configurable via `WHISPER_MODEL_SIZE`).
- **Performance:** Fast (~0.5s latency), highly accurate, flexible vocabulary.
- **Privacy:** 100% offline; no audio data leaves the machine.

### Tier 2 (Fallback): Vosk
- **Model:** `vosk-model-small-en-us-0.15`
- **Performance:** Ultra-low latency (near-instant).
- **Privacy:** 100% offline.
- **Special Feature:** Grammar-lockable for near 100% accuracy on specific wake words.

### Tier 3 (Last Resort): Google Speech API
- **Library:** `SpeechRecognition`
- **Performance:** High accuracy but requires internet and has significant latency (1-3 seconds).
- **Privacy:** Audio is sent to Google for processing.

---

## 2. How to Switch Engines

The system evaluates engines down the stack based on availability and configuration. To explicitly set the primary engine:

1. Open `.env` or `auhip/core/config.py`.
2. Change the `STT_ENGINE` variable:
   - `STT_ENGINE = "whisper"` (Default: Fast, Local, Accurate)
   - `STT_ENGINE = "vosk"` (Ultra-fast, Local, Grammar support)
   - `STT_ENGINE = "google"` (Cloud: High Accuracy, Slow)

---

## 3. Advanced Feature: Vocabulary Locking (Grammar)

To solve the issue of "near-miss" mishearings (e.g., mishearing "daddy home" as "the home"), the system supports **Grammar Locking** when using the Vosk engine. 

*(Note: When `STT_ENGINE` is set to `whisper`, passing a grammar list to `listen_for_command` will automatically fall back to the Vosk engine for that specific command to guarantee exact matches).*

### How it works:

When auhip is in a critical state (like waiting for a Wake Word), the `listen_for_command` method accepts a `grammar` list.

```python
# Example from state_machine.py
text = await self.speech_recognizer.listen_for_command(
    timeout=config.WAKE_WORD_TIMEOUT,
    phrase_time_limit=config.WAKE_WORD_TIMEOUT,
    grammar=[config.WAKE_PHRASE, config.EXIT_PHRASE],
    validator=self.agent.is_valid_command,
    mic=self.mic
)
```

By providing this list, Vosk is forced to ignore the rest of the English dictionary and only match your voice against those specific words. This results in **nearly 100% accuracy** for activation commands.

---

## 4. Technical Implementation Details

- **Audio Format:** Speech recognizers require `int16` mono audio at the model's native sample rate (matching `config.SAMPLERATE`).
- **Stream Handling:** The `SpeechRecognizer` uses a shared PyAudio queue for threaded reads to bypass standard OS overhead and share the mic with the snap detector.
- **Auto Fallback:** The initialization logic automatically steps down from Whisper -> Vosk -> Google Cloud if dependencies (like `faster-whisper`) or local models are missing.
