# auhip — Personal AI Executive Assistant

A Python-based personal assistant with double-snap activation, offline voice recognition, computer vision gestures, and a hybrid local-first LLM brain.

---

## Features

- **Double-Snap Activation** — Energy-based microphone snap detection to wake up without pressing anything
- **Hybrid Speech Recognition** — Fast local Vosk engine with Google Cloud Speech fallback
- **Local-First LLM** — Ollama-powered intent routing with automatic Gemini cloud escalation
- **Gesture Control** — MediaPipe hand tracking for Camera Mode and cursor Control Mode
- **Event-Driven Architecture** — Fully decoupled async modules over an internal event bus
- **Dark / Light Theme** — Toggle live from the nav bar (🌙 button)
- **Live System Stats** — CPU & RAM monitor in the left panel

---

## Installation

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Download Vosk speech model

- Go to [alphacephei.com/vosk/models](https://alphacephei.com/vosk/models)
- Download `vosk-model-small-en-us-0.15`
- Extract it to the project root (folder must be named `vosk-model-small-en-us-0.15`)

### 3. Install Ollama and pull a model

```bash
# Install Ollama from https://ollama.com
ollama pull qwen2.5:3b   # recommended — fast, good tool calling, ~2.5 GB
ollama serve             # keep running in background
```

### 4. Configure `.env`

Copy `.env.example` to `.env` and fill in your values:

```ini
OLLAMA_BASE_URL="http://localhost:11434"
LOCAL_MODEL_NAME="qwen2.5:3b"
LOCAL_TIMEOUT_SECONDS=45.0
GOOGLE_API_KEY="your-gemini-api-key"   # optional cloud fallback
```

### 5. Run

```bash
python main.py
```

---

## Quick Start

1. App opens and waits in Standby
2. **Snap twice** → enters Sleep mode, displays snap dots
3. Say **"daddy home"** → activates Voice Mode
4. Speak any command → auhip responds
5. Say **"goodbye jojo"** → returns to Sleep

---

## Customization Guide

### 🧠 Personality & Conversation Style — `user/identity.md`

This is the **system prompt** injected at the top of every LLM call. It shapes tone, name, priorities, and behavior. Edit it freely — no code changes needed.

**Key sections to personalize:**

```markdown
### User Name
Master              ← change to your name

### Personality
- Jarvis-like       ← change archetype (e.g. "casual friend", "sarcastic", "formal")
- Calm and analytical

### Communication Style
- Short             ← change to "detailed" if you want longer answers
- Casual English    ← change to "formal" or your preferred style
```

Changes take effect on the **next voice command** — no restart needed.

---

### ⚙️ LLM Behaviour Knobs — `.env`

| Variable | Default | Effect |
|---|---|---|
| `LOCAL_MODEL_NAME` | `qwen2.5:3b` | Which Ollama model to use |
| `LOCAL_TIMEOUT_SECONDS` | `45.0` | Timeout before falling back to Gemini |
| `ESCALATION_CONFIDENCE_THRESHOLD` | `0.70` | Raise → trust local LLM more; lower → escalate to Gemini more |
| `MAX_HISTORY_MESSAGES` | `12` | Conversation memory depth |
| `TOKEN_BUDGET_ESTIMATE` | `4096` | Raise to `8192` for longer context |
| `WEATHER_CITY` | *(blank)* | Default city for weather (blank = auto-detect from IP) |
| `TIMER_CHIME` | `true` | Show 🔔 prefix on timer-done notification |

**Recommended model alternatives:**

```bash
ollama pull qwen2.5:7b      # best quality, needs ~5 GB VRAM
ollama pull llama3.2:3b     # good alternative for 3b class
ollama pull mistral:7b-instruct  # excellent JSON compliance
```

---

### 🎯 Control When Gemini Takes Over — `auhip/core/llm/escalation.py`

Edit the `complex_triggers` list. Any phrase matching these strings **always escalates** to Gemini:

```python
complex_triggers = [
    "write code", "generate code", "refactor",
    "plan architecture", "deep analysis",
    # add your own:
    "explain why",
    "compare",
    "summarize",
]
```

Or change `ESCALATION_CONFIDENCE_THRESHOLD` in `.env` instead (simpler).

---

### 🔧 Adding a New Voice Skill

**Step 1 — Write the function** in `auhip/skills/` (any file):

```python
# auhip/skills/productivity.py
async def my_new_skill(param: str = "") -> str:
    """Short description — this is what the LLM reads to decide when to use this."""
    return f"Result: {param}"
```

**Step 2 — Export it** in `auhip/skills/__init__.py`:

```python
from .productivity import set_timer, open_app, my_new_skill
```

**Step 3 — Register it** in `auhip/core/agent.py` inside the appropriate `_register_*_tools()` method:

```python
self.tool_manager.register_tool(
    ToolSchema(
        "my_new_skill",
        "Description the LLM uses to pick this tool.",
        parameters={"param": {"type": "string", "description": "What param means."}},
        required=["param"]
    ),
    my_new_skill
)
```

**Step 4 — Add a keyword shortcut** in `_local_route()` (optional but faster, bypasses LLM):

```python
# Simple (no args):
(["my trigger phrase"], my_new_skill),

# Parameterised:
if "my trigger" in text:
    param = text.split("my trigger", 1)[-1].strip()
    return await my_new_skill(param)
```

Done. Saying **"my trigger hello"** now calls the skill instantly without hitting the LLM.

---

### 🌤️ Wake Phrase — Developer Panel (GUI)

The default wake phrase is `"daddy home"`. To change it at runtime:
1. Open the **Developer Tools** bar at the bottom of the window
2. Find the **Config** row
3. Edit the **Wake phrase** field and click **Apply**

The change takes effect immediately on the next listen cycle. To make it permanent, edit `WAKE_PHRASE` in `auhip/core/config.py`.

---

### 🌡️ LLM Temperature — `auhip/core/llm/local_model.py` line 94

```python
"temperature": 0.4,   # raise to 0.7 for more creative replies
                       # lower to 0.2 for strict command accuracy
```

---

## Architecture

```
auhip/
├── audio/          Microphone, snap detector, speech recognition
├── core/
│   ├── agent.py    Skill registry + local keyword router
│   ├── config.py   All runtime config constants
│   ├── event_bus.py Async pub/sub event system
│   ├── llm/        Ollama adapter, Gemini fallback, prompt builder
│   └── state_machine.py  Mode transitions (Voice/Camera/Control/Sleep)
├── gui/            PyQt6 UI — nav bar, panels, theme system
├── skills/         All callable voice skills (information, productivity, etc.)
├── vision/         MediaPipe hand/eye tracking, gesture engine
└── docs/           Technical documentation

user/
└── identity.md     Your AI persona config (edit freely)

.agents/
└── context.md      Project context injected into every LLM prompt
```

---

## Voice Command Reference

| Say | Action |
|---|---|
| `"daddy home"` | Activate Voice Mode |
| `"what time is it"` | Current time |
| `"what's today"` | Today's date |
| `"weather"` / `"weather in [city]"` | Current weather |
| `"set a timer for 5 minutes"` | Countdown timer |
| `"open notepad"` / `"launch chrome"` | Open any app |
| `"open youtube music"` | Open YouTube Music |
| `"search youtube music for [query]"` | Search YouTube Music |
| `"volume up"` / `"volume down"` | System volume |
| `"take a screenshot"` | Capture screen |
| `"status"` | CPU & RAM usage |
| `"help"` | List all commands |
| `"camera on"` | Enter Camera Mode (gestures) |
| `"control on"` | Enter Control Mode (cursor) |
| `"goodbye jojo"` | Sleep Mode |
