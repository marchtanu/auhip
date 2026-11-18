# AUHIP

AUHIP is a Windows desktop voice assistant built with Python and PyQt6. It combines a voice interface, local LLM routing, productivity and workspace tools, and optional camera-based gestures. The desktop app is the primary supported runtime; the daemon/client pair is experimental.

## Capabilities

- Ambient voice HUD and developer cockpit, coordinated by an async state machine and event bus.
- Speech recognition through faster-whisper or Vosk, with Edge TTS or local pyttsx3 output.
- Local Ollama model routing, with optional Gemini cloud fallback and Gemini Live voice.
- Workspace, task, calendar, web, and system-control tools.
- Optional OpenCV/MediaPipe camera and air-mouse modes.

Some integrations need network access. In particular, Edge TTS, Gemini, weather/search tools, and first-time Whisper model downloads are not offline. For a local LLM, install Ollama and pull a model separately.

## Setup (Windows 10/11)

Use Python 3.10 or 3.11. Create a virtual environment, install dependencies, and configure the environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Install [Ollama](https://ollama.com), then pull a model and start its local service:

```powershell
ollama pull qwen2.5:7b
ollama serve
```

Edit `.env` to set `LOCAL_MODEL_NAME` to a model you have installed. The default voice engine is `classic` when using the supplied example configuration. The default local speech recognition engine uses faster-whisper and may download its model the first time it runs. For Vosk, set `STT_ENGINE=vosk`; the small English model directory is included in this repository.

## Run

```powershell
# Desktop GUI, immediately active
python main.py --direct

# Hidden standby listener
python main.py --standby

# Select voice implementation for this launch
python main.py --classic
python main.py --live
```

`--live` requires `CLOUD_ENABLED=true`, `GOOGLE_API_KEY` or `GEMINI_API_KEY`, and approval of the audio-sharing prompt in the desktop app. Live sends microphone audio and the ongoing session conversation to Google until stopped. It is a cloud conversation without access to saved memories, identity files, or local desktop tools; use classic mode for local actions. If Live is disabled or denied, the desktop uses classic mode. Classic is the code and example-configuration default.

The classic voice path uses local speech recognition and Ollama, but Edge TTS requires network access unless `TTS_ENGINE=pyttsx3` is selected. The daemon and WebSocket command-palette client can be launched separately with `python -m auhip.daemon.main` and `python -m auhip.client.main`; that split has less complete lifecycle handling and is not the primary runtime. The standalone Live client uses the same audio engine and requires `python -m auhip.tools.gemini_live --accept-audio-sharing` in addition to the cloud setting and API key.

## Configuration

See [`.env.example`](.env.example). Useful settings include:

| Variable | Purpose |
|---|---|
| `VOICE_MODE_ENGINE` | `classic` or `gemini_live` |
| `STT_ENGINE` | `whisper`, `vosk`, or the supported cloud recognizer |
| `LOCAL_MODEL_NAME` | Installed Ollama model tag |
| `CLOUD_ENABLED` | Master opt-in for explicitly requested Gemini work; defaults to disabled |
| `GOOGLE_API_KEY` | Gemini key for cloud fallback or Gemini Live |
| `SECOND_BRAIN_PATH` | Optional location of the separate personal workspace |
| `AUHIP_EMBEDDING_MODEL` | Local Ollama embedding model for semantic memory search (`nomic-embed-text`) |
| `AUHIP_EMBEDDING_DIMENSION` | Expected local embedding width (`768` for `nomic-embed-text`) |
| `AUHIP_ALLOW_UNSAFE_TOOLS` | Bypasses the desktop approval prompt; leave unset for interactive review |

Workspace writes, patches, deletions, and arbitrary PowerShell execution require a per-action approval in the desktop GUI, including deterministic voice shortcuts. Headless mode denies them unless `AUHIP_ALLOW_UNSAFE_TOOLS=true` is set. That environment variable bypasses tool prompts, so keep it unset for normal use; it does not bypass Live audio-sharing approval. Cloud inference is disabled by default. Classic-mode requests to use Gemini send the current prompt only, not saved memories or previous turns. Live mode has the distinct session audio-sharing boundary described above.

Typed cockpit input, voice input, and IPC goals use the same agent/tool execution path. Long plans run outside the event dispatcher so approvals and cancellation can still be delivered. Denied or failed plan steps stop dependent work. Cancellation interrupts pending approvals and asynchronous actions; actions already completed are not undone, and a synchronous system call already running may finish.

## Local verification

Run `python tests/run_local_checks.py` after installing the dependencies. It runs the behavioral regression checks, interface checks in hidden windows, and the older audit checks with temporary data and simulated network/device actions. It does not start real voice recognition, stream audio to Gemini, or dispatch a coding agent. The same command runs in Windows CI. See [the reliability notes](docs/RELIABILITY.md) for coverage and remaining manual checks.

## Local memory

AUHIP automatically recalls only curated facts, preferences, decisions, and project memories. It does not promote every conversation into long-term memory. Say “remember that …” to save one explicitly; ask to list, correct, or forget a saved memory. Memory entries include a stable ID, source, date, type, and confidence. Deleting a memory requires confirmation.

Conversation excerpts, second-brain documents, AUHIP project guidance, and agent task receipts have separate retrieval paths. Second-brain search returns source file and line references; task history reads only `.auhip/handoff/` receipts. Retrieved content is treated as data, never as instructions.

For semantic personal-memory ranking, install LanceDB from the project dependencies and run `ollama pull nomic-embed-text`. If the embedding model or vector index is unavailable, AUHIP uses BM25-style local keyword ranking; it never substitutes a zero vector. Embeddings are local and use a separate versioned vector table so the older truncated 384-dimensional index is not mixed in. See [`evals/local_brain_scorecard.json`](evals/local_brain_scorecard.json) for repeatable recall, source-selection, delegation, and cloud-consent checks.

## Architecture

```text
PyQt GUI ── EventBus ── State machine / Agent ── ToolManager ── skills
                              │                    │
                      audio + speech          local Ollama /
                      camera + vision          optional Gemini
```

Key locations:

- `auhip/core/state_machine.py` — state transitions and voice lifecycle
- `auhip/core/event_bus.py` — asynchronous component events
- `auhip/core/agent.py` and `auhip/core/llm/` — routing and tool registration
- `auhip/audio/`, `auhip/vision/`, and `auhip/gui/` — device and interface components
- `auhip/daemon/` and `auhip/client/` — experimental split-process runtime

The `Procfile`/Railpack deployment files are not a supported hosting path: this application expects an interactive Windows desktop, audio devices, and often a camera.

## Coding-agent handoff

Cross-agent context lives in [`AUHIP-context.md`](AUHIP-context.md), with the shared `auhip-handoff` skill at `.agents/skills/auhip-handoff/SKILL.md`. After a delegated task, an agent can save a JSON receipt and ask a running AUHIP instance to announce the result:

```powershell
python -m auhip.tools.handoff complete --task-id auhip-104 --status completed --summary "Fixed the redirect bug" --file "src/auth/redirect.ts" --check "unit tests: passed"
```

Receipts are written under `.auhip/handoff/` and are ignored by Git. Run `python -m auhip.tools.handoff speak --text "Your message"` to send a short announcement directly. The AUHIP desktop app or daemon must be running for the announcement; receipts remain saved if it is offline. `AUHIP_HANDOFF_DIR` and `AUHIP_IPC_URI` can override the local receipt directory and loopback endpoint.

### Dispatch work to Antigravity

AUHIP can queue a task through the installed Antigravity CLI. Ask AUHIP to send a task to Antigravity; it requests approval before starting. The default workspace is the AUHIP repository. You can provide another absolute workspace path only if it falls inside a configured `SANDBOX_ALLOWED_DIRS` root. Install and authenticate Antigravity CLI so `agy` is available on AUHIP's `PATH`, or set `AUHIP_ANTIGRAVITY_CLI` to its executable path. The task runs with Antigravity's sandbox enabled and returns its completion through the AUHIP handoff receipt. Prompts are sent to Antigravity's hosted agent service.

## Data and privacy

Personal task/calendar data is stored under `data/`; runtime logs and screenshots may also contain private information. Keep those out of public source distributions. `.env` is ignored by Git; never place API keys in tracked files.
