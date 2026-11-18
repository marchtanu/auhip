# Speech Recognition System (v2.4 Upgrade)

AUHIP features a next-generation hybrid speech recognition architecture that delivers sub-second local transcription, domain vocabulary prompt biasing, and anti-hallucination protection. It operates as a flexible 3-tier system:

---

## 1. Recognition Engines (3-Tier Stack)

### 🥇 Tier 1 (Primary): Upgraded Faster-Whisper
- **Models Supported:**
  - `base.en` (Default recommended): English-specialized, ~74 MB, ~0.35s latency, high precision.
  - `small.en`: Higher accuracy for noisy environments (~244 MB).
  - `distil-small.en` / `distil-large-v3`: Distil-Whisper models for ultra-low latency with near-zero accuracy loss.
  - `turbo`: Latest OpenAI Whisper Large-v3-Turbo architecture (~4x faster than original Large-v3).
  - `base`: Multilingual fallback model.
- **Vocabulary Prompt Biasing (`initial_prompt`):** Instructs the decoder on AUHIP assistant keywords (`"daddy home"`, `"goodbye jojo"`, `"air mouse"`, `"cockpit"`, `"workspace"`, `"directory tree"`) preventing near-miss phonetic transcription errors.
- **Anti-Hallucination Guards:**
  - `condition_on_previous_text=False`: Prevents runaway repetition loops on background silence.
  - `repetition_penalty=1.15`: Penalizes repetitive phrases.
  - `no_speech_threshold=0.6`: Discards microphone line hum.
  - `compression_ratio_threshold=2.4`: Automatically rejects degenerate hallucination patterns.
- **Dual-Tier VAD:** Fast RMS energy thresholding + built-in Silero Neural VAD segmentation (`vad_filter=True`).
- **Privacy:** 100% offline; runs entirely on local CPU (`int8`) or GPU (`cuda`).

### 🥈 Tier 2 (Fallback): Vosk
- **Model:** `vosk-model-small-en-us-0.15` (~40 MB).
- **Performance:** Instantaneous (<100ms), lightweight offline execution.
- **Special Feature:** Grammar-lockable for 100% precision on specific wake words (`["daddy home", "exit", "[unk]"]`).

### 🥉 Tier 3 (Last Resort): Google Speech API
- **Library:** `SpeechRecognition`
- **Performance:** Cloud fallback with broad vocabulary (requires internet connectivity).

---

## 2. Configuration & Model Switching

Configure your primary engine and model in `.env` or `auhip/core/config.py`:

```ini
# Primary Engine: "whisper" (recommended), "vosk", or "google"
STT_ENGINE="whisper"

# Faster-Whisper Model: "base.en", "small.en", "distil-small.en", "turbo", "base"
WHISPER_MODEL_SIZE="base.en"

# Compute Device & Quantisation
WHISPER_DEVICE="cpu"
WHISPER_COMPUTE_TYPE="int8"
```

### 🎛️ Live Runtime Model Switching in Cockpit
You can switch Whisper models or switch between Whisper and Vosk live without restarting the application:
1. Open the Developer Cockpit (`F2` or `Ctrl+Tab`).
2. Expand the bottom **`DEBUG & CONTROLS`** drawer.
3. Select any model from the **STT** dropdown:
   - `Whisper (base.en)`
   - `Whisper (small.en)`
   - `Whisper (distil-small.en)`
   - `Whisper (turbo)`
   - `Vosk (offline)`
4. The background recognizer hot-swaps the underlying model in a non-blocking thread.

---

## 3. Advanced Vocabulary Prompt Biasing

Unlike generic speech models that struggle with wake words and technical jargon, AUHIP biases Whisper's initial decoding tokens:

```python
DEFAULT_INITIAL_PROMPT = (
    "AUHIP executive assistant. Voice commands: daddy home, goodbye jojo, open camera, "
    "control mode, air mouse, cockpit, workspace, analyze my project, view directory tree, "
    "search codebase, list tasks, add task, complete task, stock, weather, YouTube Music."
)
```

This guarantees accurate detection even when whispered or spoken in noisy environments.
