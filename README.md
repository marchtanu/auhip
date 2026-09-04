# auhip — Personal AI Executive Assistant (v2.4 OS)

A next-generation personal AI assistant blending **OpenAI Voice-style conversational flow**, a **dual-mode interface** (Minimalist Atmospheric Voice HUD ⮀ Light-Mode Developer Cockpit), **contactless Air-Mouse gesture control**, and an **agentic local-first LLM brain** running on your local GPU.

---

## 🌟 Key Features

- **Dual-Mode User Interface:**
  - **Mode A (Ambient Voice HUD):** Minimal full-screen 16:9 interface with a 380–450px volumetric AI orb, 3-layer internal flowing plasma/clouds, 92-bar symmetrical horizontal audio visualizer, 75% frosted-glass navbar, and live speech transcription.
  - **Mode B (Developer Cockpit):** Premium editorial workstation built per `docs/DESIGN.md`. Features a System Status Card with mini orb, Bento prioritization deck, switchable center workspaces (`💬 Chat`, `👁️ Vision & Air-Mouse HUD`, `📁 Workspace Explorer`), Command History, and an in-app User Guide modal.
  - **Instant Hotkey:** Press `Ctrl+Tab` or `F2` to toggle modes instantaneously.
- **Conversational Voice & Barge-In:** Continuous turn-taking dialogue without repeating wake words; instant audio cut-off when the user interrupts or speaks.
- **Contactless Air-Mouse (Control Mode):** Point your index finger forward to move the cursor with sub-pixel 1€ filtering; pinch index & thumb to click; pinch and hold to drag; closed fist to scroll; rock-on sign (🤘) to exit.
- **Local-First GPU Brain:** Powered by Ollama (`qwen2.5:7b` recommended) for offline privacy, instant tool calling, and high-speed execution (~50 tok/s).
- **Agentic Workspace Tools:** Autonomous code inspection, file editing, directory tree rendering, pattern searching, and guarded PowerShell execution.
- **Private NotebookLM Capabilities:** Local document summarization, executive briefings, and dual-host AI audio overviews (podcasts) using Edge-TTS neural voices.
- **Hardware Optimization:** Camera and MediaPipe models are completely unpowered when not in vision modes (`CAMERA_ON_DEMAND`).

---

## 🚀 Quick Installation

### 1. Clone & Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Download Offline Vosk Speech Model

1. Download `vosk-model-small-en-us-0.15` from [alphacephei.com/vosk/models](https://alphacephei.com/vosk/models).
2. Extract the model directory directly into the project root:
   ```text
   Jarvis_demo/vosk-model-small-en-us-0.15/
   ```

### 3. Setup Local LLM (Ollama)

```bash
# Install Ollama from https://ollama.com
ollama pull qwen2.5:7b   # Recommended for RTX 3060 (6GB VRAM)
ollama serve             # Keep running in background
```

### 4. Configure `.env`

Copy `.env.example` to `.env`:

```ini
OLLAMA_BASE_URL="http://localhost:11434"
LOCAL_MODEL_NAME="qwen2.5:7b"
LOCAL_TIMEOUT_SECONDS=45.0
GOOGLE_API_KEY="your-gemini-api-key"   # Optional cloud fallback
```

### 5. Launch

```bash
# Direct Interactive Mode (bypasses double-snap wait)
python main.py --direct

# Standby Double-Snap Wake Mode
python main.py
```

---

## 🎮 How to Interact

### 🎙️ Voice Flow
1. Say **"daddy home"** to wake up the assistant.
2. Speak naturally — AUHIP responds with continuous turn-taking. Interrupt anytime to barge in.
3. Say **"goodbye jojo"** to put the assistant to sleep.

### 🕹️ Mode Switching
- Say **"cockpit"** or press **`F2`** / **`Ctrl+Tab`** to open the Developer Cockpit.
- Say **"control mode"** or click **`[ 🎮 Enter Air-Mouse Mode ]`** to control your mouse pointer with your index finger.
- Say **"open camera"** to enter the Vision & Attention HUD.
- Say **"voice mode"** to return to the minimal Ambient Voice HUD.

### 📁 Agentic & Workspace Skills
- *"analyze my project"* — Scans workspace and reports health.
- *"view directory tree"* — Generates visual codebase hierarchy.
- *"search codebase [term]"* — Finds matching lines across code files.
- *"find unused files"* — Detects orphaned Python modules.
- *"summarize notebook"* — Generates executive briefing from local documents.
- *"audio overview"* — Generates a dual-host AI podcast dialogue.
- *"add task [title]"* / *"list tasks"* / *"complete task [id]"* — Task manager organizer.

---

## 🏛️ System Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        AUHIP DUAL-MODE PYQT6 UI                        │
│   [Mode A: Ambient Voice Orb]        [Mode B: Developer Cockpit]       │
│   - 380px Volumetric Gas Orb         - Bento Priority Decks            │
│   - 92-Bar Audio Visualizer          - Chat / Vision HUD / Explorer    │
│   - 75% Frosted-Glass Navbar         - Interactive User Guide Modal    │
└───────────────────┬────────────────────────────────┬───────────────────┘
                    │ EventBus                       │ EventBus
                    ▼                                ▼
┌────────────────────────────────────────────────────────────────────────┐
│                    AUHIP ASYNC ORCHESTRATION LAYER                     │
│  - Finite State Machine (STANDBY ⮀ VOICE ⮀ CAMERA ⮀ CONTROL ⮀ SLEEP)   │
│  - Continuous Turn-Taking & Acoustic Energy Barge-In Detector          │
│  - Guarded Tool Registry & Sandbox Execution Engine                    │
└───────────────────┬────────────────────────────────┬───────────────────┘
                    │                                │
                    ▼                                ▼
┌──────────────────────────────────────┐  ┌──────────────────────────────┐
│       VISION & AIR-MOUSE ENGINE      │  │    LOCAL OLLAMA BRAIN (GPU)  │
│  - MediaPipe 21-point hand tracking  │  │  - qwen2.5:7b (~50 tok/s)    │
│  - Sub-pixel 1€ OneEuroFilter cursor │  │  - Fast parameterless routes │
│  - On-Demand Power Throttling        │  │  - Local NotebookLM RAG      │
└──────────────────────────────────────┘  └──────────────────────────────┘
```

---

## 🧪 Automated Testing

```bash
# Run comprehensive audit and architectural polish verification
python tests/test_audit_fixes.py
python tests/test_polish_and_alignment.py

# Agentic skills and workspace tool suite
python tests/test_agentic_skills.py

# Cockpit suite & Guide Modal tests
python tests/test_cockpit_view.py

# Ambient Voice UI visualizer & orb tests
python tests/test_ambient_ui.py

# Acoustic Barge-In & turn-taking tests
python tests/test_barge_in.py
```

