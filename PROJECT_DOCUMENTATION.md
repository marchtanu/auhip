# AUHIP (Jarvis_demo) — Comprehensive System Documentation

> **System Name:** AUHIP Executive Personal Assistant (`Jarvis_demo`)  
> **Version:** 2.4.0 (Next-Generation Dual-Mode OS)  
> **Architecture:** Decoupled Event-Driven Async System with Local-First Hybrid LLM Brain, Computer Vision Air-Mouse, and Dual-Mode UI  

---

## 📋 Table of Contents

1. [Project Overview & Architectural Context](#1-project-overview--architectural-context)
2. [Full Operating Instructions & Setup](#2-full-operating-instructions--setup)
3. [Dual-Mode User Interface & Visual Layout](#3-dual-mode-user-interface--visual-layout)
4. [Computer Vision & Contactless Air-Mouse](#4-computer-vision--contactless-air-mouse)
5. [Conversational Flow, Turn-Taking & Acoustic Barge-In](#5-conversational-flow-turn-taking--acoustic-barge-in)
6. [Unified Voice Command Routing Engine](#6-unified-voice-command-routing-engine)
7. [Multi-Agent Orchestration & Memory Architecture](#7-multi-agent-orchestration--memory-architecture)
8. [Complete 38-Tool Agentic Catalog](#8-complete-38-tool-agentic-catalog)
9. [Local NotebookLM Capabilities](#9-local-notebooklm-capabilities)
10. [Finite State Machine (FSM) & State Logic](#10-finite-state-machine-fsm--state-logic)
11. [Event Bus Wiring & Communication Matrix](#11-event-bus-wiring--communication-matrix)
12. [Keyboard Shortcuts & Quick Reference](#12-keyboard-shortcuts--quick-reference)
13. [System Hardening & Audit Verification](#13-system-hardening--audit-verification)

---

## 1. Project Overview & Architectural Context

**AUHIP** is an intelligent, privacy-focused executive personal assistant built in Python. It integrates zero-click acoustic wake-up (double-snap detection), offline speech-to-text (STT), computer-vision gesture recognition, contactless Air-Mouse desktop control, and a hybrid local-first Large Language Model (LLM) orchestration engine running on your local GPU (NVIDIA RTX 3060).

### 🌟 Key Architectural Pillars

* **Dual-Mode Experience:** Seamlessly switches between a cinematic, minimalist **Ambient Voice HUD** (floating volumetric plasma orb + continuous waveform) and a high-efficiency light-mode **Developer Cockpit** (Bento cards, workspace explorer, camera HUD, and task organizer).
* **Local-First Processing:** Core voice recognition and primary LLM intent routing run entirely locally using [Vosk](https://alphacephei.com/vosk/) and [Ollama](https://ollama.com) (`qwen2.5:7b`), ensuring ~50 tok/s generation speeds, complete offline privacy, and zero external subscription fees.
* **Continuous Turn-Taking & Instant Barge-In:** Natural OpenAI Voice-style conversation loop. The user speaks without repeating wake words, and any interruption instantly cuts off the text-to-speech (TTS) audio stream via energy-onset detection.
* **Contactless Air-Mouse (Control Mode):** Real-time 21-point MediaPipe hand tracking with sub-pixel 1€ OneEuroFilter smoothing. Single index finger pointing moves the desktop cursor, pinching index & thumb clicks, holding drags, and closed-fist gestures scroll.
* **Agentic Workspace Tools:** Autonomous code inspection, file patching, directory tree generation, pattern search, and guarded PowerShell execution.
* **Hardware Power Optimization:** Camera and MediaPipe models are unpowered when not in vision modes (`CAMERA_ON_DEMAND = True`), saving laptop battery and GPU VRAM.

---

## 2. Full Operating Instructions & Setup

### 🛠️ Hardware & Software Requirements

* **OS:** Windows 10/11 (64-bit).
* **Python:** Python 3.10 or 3.11.
* **Microphone & Webcam:** Any standard USB microphone/headset and webcam.
* **Ollama:** Installed locally for offline GPU inference (`qwen2.5:7b` recommended).

---

### 🚀 Installation

```bash
# 1. Install Python packages
pip install -r requirements.txt

# 2. Download offline Vosk model into project root
# Download 'vosk-model-small-en-us-0.15' from https://alphacephei.com/vosk/models
# Extract to Jarvis_demo/vosk-model-small-en-us-0.15/

# 3. Pull recommended Ollama model
ollama pull qwen2.5:7b
ollama serve

# 4. Copy .env
copy .env.example .env
```

### 🎬 How to Launch

```bash
# Direct Interactive Mode (bypasses double-snap wait)
python main.py --direct

# Standby Double-Snap Wake Mode
python main.py
```

---

## 3. Dual-Mode User Interface & Visual Layout

AUHIP features a dual-mode UI managed by a master `QStackedWidget` in [`auhip/gui/main_window.py`](file:///d:/Desktop/Code/personal/project/Jarvis_demo/auhip/gui/main_window.py). Pressing **`F2`** or **`Ctrl+Tab`** instantaneously flips between the two modes:

### Mode A: Minimalist Atmospheric Voice HUD (`AmbientVoiceView`)
Designed for immersion, screen casting, and ambient presence:
* **Atmospheric Palette:** Soft lavender, periwinkle, and pale blue atmospheric gradient background.
* **Top Navigation Bar:** Floating frosted-glass pill bar centered at ~75% screen width:
  `✦ auhip` logo · `v2.4 OS` badge · Last command preview · Digital clock · `● Ready` · Mode switcher button `[ 🎛️ Cockpit ]`.
* **Status Section:** Centered status header (`STATUS`) with mode labels (`Listening`, `Thinking`, `Speaking`, `Ready`) and 3 pulsing dots (`● ● ●`).
* **Volumetric AI Orb:** 380–450px floating orb with 3-layer internal flowing liquid plasma and cloud mist with soft blurred ground shadow.
* **Continuous Audio Waveform:** 92-bar symmetrical horizontal audio visualizer positioned behind the orb with louder peak clusters.
* **Live Transcription Feed:** Centered real-time speech text with glowing pulsing indicator dot.

### Mode B: Modern Light-Mode Developer Cockpit (`CockpitView`)
Designed per `docs/DESIGN.md` for intensive engineering and productivity:
* **Left Column (System Status Card):** Real-time FSM state badge, mic/TTS status, snap detection counter, CPU/RAM/GPU activity gauges, and an embedded mini ambient gas orb.
* **Top Bento Cards:**
  * *Priorities Card:* Shows high-priority to-do items. Clicking `View all tasks →` opens the interactive `TaskManagerModal`.
  * *In Progress Card:* Live project progress bar with direct link to Workspace Explorer.
  * *System Overview:* Local Ollama model status (`qwen2.5:7b`), VRAM allocation, and system uptime.
* **Center Stack Deck (Switchable Workspaces):**
  1. `💬 Chat Workspace:` Conversational feed, step checklist, and prompt input bar.
  2. `👁️ Vision & Air-Mouse HUD:` Live camera canvas, iris gaze telemetry, blink detection, and contactless Air-Mouse controls.
  3. `📁 Workspace Explorer:` File tree inspector, syntax-highlighted code viewer, and unused file scanner.
* **Right Column:** Command History (click any entry to immediately re-run) and Active Sub-Agents deck.
* **Bottom Drawer:** Collapsible Debug Controls, hardware overrides, mode switchers, and real-time event stream.
* **In-App Guide:** Interactive `[ 📖 User Guide & Shortcuts ]` modal detailing all gestures, commands, and layout features.

---

## 4. Computer Vision & Contactless Air-Mouse

Managed by [`VisionWorker`](file:///d:/Desktop/Code/personal/project/Jarvis_demo/auhip/vision/worker.py) with OpenCV and MediaPipe Hands:

### Control Mode (Air-Mouse) Gestures
* ☝️ **Point Index Finger:** Moves the desktop mouse cursor smoothly with sub-pixel 1€ OneEuroFilter smoothing.
* 🎯 **Fingertip Target Overlay:** A live green/cyan target ring and crosshair ticks follow your fingertip on the camera canvas.
* 🤏 **Index + Thumb Pinch (<0.5s):** Immediate left-click.
* ✊ **Pinch & Hold (≥0.5s):** Left mouse button down (drag & drop). Release pinch to drop.
* ✌️ **Double Pinch (within 0.4s):** Double-click.
* ✊ **Move Fist Up / Down:** Smooth vertical page scrolling.
* 🤘 **Rock-On Sign (🤘 Index + Pinky up):** Exit Air-Mouse mode back to Voice Mode.

---

## 5. Conversational Flow, Turn-Taking & Acoustic Barge-In

AUHIP provides an OpenAI Voice-style conversational loop in [`AuhipStateMachine`](file:///d:/Desktop/Code/personal/project/Jarvis_demo/auhip/core/state_machine.py):
1. **Continuous Turn-Taking:** Once activated (via `"daddy home"` or `--direct`), the assistant continuously listens after speaking its response, eliminating the need to repeat wake words on every turn.
2. **Instant Acoustic Barge-In:** [`EdgeTTSPlayer`](file:///d:/Desktop/Code/personal/project/Jarvis_demo/auhip/audio/tts.py) monitors acoustic energy. If the user speaks while the assistant is talking, audio playback stops immediately (<50ms) and voice recognition begins processing the new query.

---

## 6. Unified Voice Command Routing Engine

Implemented in [`auhip/core/voice_commands.py`](file:///d:/Desktop/Code/personal/project/Jarvis_demo/auhip/core/voice_commands.py):
The single source of truth for all voice commands across AUHIP, eliminating dual-route drift between [`AuhipAgent`](file:///d:/Desktop/Code/personal/project/Jarvis_demo/auhip/core/agent.py) and [`SupervisorAgent`](file:///d:/Desktop/Code/personal/project/Jarvis_demo/auhip/core/agents/supervisor.py).

* **Canonical Parameterless Route Table:** 36 route definitions mapping directly to native async handlers.
* **Derived Valid Keywords:** Over 210 keyword phrases automatically built and synchronized for the speech recognizer grammar.
* **Parameterised Skill Dispatching:** Handlers for dynamic voice queries with argument extraction:
  * Weather: `"weather in Tokyo"` / `"forecast for London"`
  * Timers: `"set a timer for 10 minutes"` / `"countdown 30 seconds"`
  * Application Launch: `"open notepad"` / `"launch calculator"`
  * YouTube Music: `"play music interstellar soundtrack"`
  * Stocks: `"stock price of NVDA"` / `"lookup stock AAPL"`
  * GitHub: `"search github python voice assistant"`
  * Tasks: `"add task review system audit"` / `"complete task 1"`
  * Files: `"read code auhip/core/config.py"` / `"delete file temp.py"`
  * Workspace: `"search codebase event_bus"` / `"run command dir"`

---

## 7. Multi-Agent Orchestration & Memory Architecture

AUHIP features a hierarchical, multi-agent reasoning architecture designed for autonomy and persistent personalization:

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                              AUHIP AGENT                                │
│        Central orchestrator & public API for state machine / GUI        │
└──────────────┬───────────────────────────────────────────┬──────────────┘
               │                                           │
               ▼                                           ▼
┌───────────────────────────────┐           ┌─────────────────────────────┐
│       SUPERVISOR AGENT        │           │        PLANNER AGENT        │
│  - Evaluates user intent      │◀─────────▶│  - Acyclic Action Graphs    │
│  - Dispatches local macros    │           │  - Step dependency check    │
│  - Delegates complex goals    │           │  - Verifies tool outcomes   │
└──────────────┬────────────────┘           └──────────────┬──────────────┘
               │                                           │
               └─────────────────────┬─────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       CENTRAL TOOL MANAGER (38 Tools)                   │
│   Unified schema registry, path isolation, and sandboxed execution     │
│   Bridged dynamically to legacy ToolRegistry singleton                  │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         PERSISTENT MEMORY AGENT                         │
│  - Working Memory: Active sub-goals and executing tool outputs          │
│  - Session Memory: Sliding window of recent dialogue exchanges          │
│  - Long-Term Memory: JSON store (`data/memory_records.json`) + LanceDB  │
│  - Context Injection: Relevant memories prepended to LLM prompt context │
└─────────────────────────────────────────────────────────────────────────┘
```

### Memory Agent Capabilities
Implemented in [`auhip/core/agents/memory.py`](file:///d:/Desktop/Code/personal/project/Jarvis_demo/auhip/core/agents/memory.py):
* **Local Atomic Persistence:** Stores memories to `data/memory_records.json` automatically, with zero external database dependencies required.
* **LanceDB Vector Store:** Seamlessly utilizes LanceDB with 384-dimensional vector embeddings when installed.
* **Lexical & Recency Fallback:** Token-overlap relevance scoring with recency and importance weighting.
* **Context Injection:** When `HybridLLMRouter` prepares a prompt, it queries `MemoryAgent` for relevant context and injects it into the prompt header.
* **Dialogue Recording:** Assistant responses and user turns are automatically captured and saved.

---

## 8. Complete 38-Tool Agentic Catalog

All 38 agentic tools are registered in [`ToolManager`](file:///d:/Desktop/Code/personal/project/Jarvis_demo/auhip/core/llm/tool_manager.py) and bridged to [`ToolRegistry`](file:///d:/Desktop/Code/personal/project/Jarvis_demo/auhip/core/tool_registry.py) with workspace sandbox protection:

| # | Tool Name | Category | Primary Function |
|---|---|---|---|
| 1 | `patch_file` | Workspace | Precise string search-and-replace code modification |
| 2 | `view_directory_tree` | Workspace | Generates formatted ASCII directory hierarchy |
| 3 | `search_codebase` | Workspace | Regex/text search across all workspace files |
| 4 | `run_powershell_guarded` | Workspace | Executes safe PowerShell commands with timeout |
| 5 | `list_workspace_files` | Workspace | Lists all files and folders in workspace |
| 6 | `read_code_file` | Workspace | Reads code file with path traversal protection |
| 7 | `write_code_file` | Workspace | Creates or overwrites code files in sandbox |
| 8 | `list_unused_files` | Workspace | Identifies unreferenced Python modules |
| 9 | `delete_file` | Workspace | Deletes files with protected system file guards |
| 10 | `search_github` | Workspace | Searches repositories on GitHub |
| 11 | `summarize_notebook` | NotebookLM | Generates executive briefings from notes |
| 12 | `generate_audio_overview` | NotebookLM | Generates dual-host AI podcast audio dialogue |
| 13 | `add_task` | Organizer | Adds a new task to the to-do list |
| 14 | `list_tasks` | Organizer | Lists pending and completed tasks |
| 15 | `complete_task` | Organizer | Marks a task completed by ID |
| 16 | `add_calendar_event` | Organizer | Adds a scheduled event to calendar |
| 17 | `list_calendar_events` | Organizer | Lists upcoming calendar events |
| 18 | `lookup_stock` | Financial | Real-time stock quote from Yahoo Finance API |
| 19 | `set_timer` | Productivity | Starts an asynchronous countdown timer |
| 20 | `open_app` | Productivity | Launches desktop applications via Windows Run |
| 21 | `tell_time` | Information | Reads the current local time |
| 22 | `tell_date` | Information | Reads today's day and date |
| 23 | `get_weather` | Information | Retrieves live weather via wttr.in |
| 24 | `search_web` | Information | Searches Google / DuckDuckGo |
| 25 | `get_help` | Information | Returns voice command cheat sheet |
| 26 | `volume_up` | System Control | Increments Windows master volume |
| 27 | `volume_down` | System Control | Decrements Windows master volume |
| 28 | `mute_volume` | System Control | Toggles master audio mute |
| 29 | `take_screenshot` | System Control | Captures screen to `screenshots/` |
| 30 | `sleep_mode` | System Control | Transitions assistant into sleep state |
| 31 | `system_status` | System Control | Reports CPU, RAM, and battery telemetry |
| 32 | `open_browser` | System Control | Launches system default browser |
| 33 | `media_play_pause` | Media | Toggles media playback (Play/Pause) |
| 34 | `media_next_track` | Media | Skips to next track |
| 35 | `media_prev_track` | Media | Returns to previous track |
| 36 | `open_youtube_music` | Media | Opens YouTube Music in browser |
| 37 | `search_youtube_music`| Media | Searches and plays music on YouTube Music |
| 38 | `toggle_light` / `smart_home` | IoT | Simulates smart home IoT automation |

---

## 9. Local NotebookLM Capabilities

Implemented per [`docs/NOTEBOOKLM_ROADMAP.md`](file:///d:/Desktop/Code/personal/project/Jarvis_demo/docs/NOTEBOOKLM_ROADMAP.md):
* **Local Ingestion:** Ingests markdown notes and documentation from `user/notebooks/` and `docs/`.
* `summarize_notebook(name: str)`: Synthesizes multi-document context into an executive briefing document.
* `generate_audio_overview(topic: str)`: Generates a natural two-speaker conversational podcast between **Alex** (British voice: `en-GB-RyanNeural`) and **Taylor** (US voice: `en-US-JennyNeural`).

---

## 10. Finite State Machine (FSM) & State Logic

Managed by [`AuhipStateMachine`](file:///d:/Desktop/Code/personal/project/Jarvis_demo/auhip/core/state_machine.py):

```text
[ STANDBY ] ──( 2 Snaps + "daddy home" )──> [ VOICE_MODE ]
     ▲                                            │   ▲
     │                               "open camera"│   │"camera off" / "exit mode"
     │                                            ▼   │
     │                                     [ CAMERA_MODE ]
     │                                            │   ▲
     │                               "control on" │   │"rock_sign" / "control off"
     │                                            ▼   │
     │                                     [ CONTROL_MODE ]
     │                                            │
"goodbye jojo"                                    │ "goodbye jojo"
     │                                            ▼
     └──────────────────────────────────── [ SLEEP ]
```

* **Continuous Listening:** In `VOICE_MODE`, the assistant continues listening across conversational turns without returning to standby (`AUTO_STANDBY_ENABLED = False`).
* **Sub-Mode Return Politeness:** Returning from camera or control mode responds with a brief "Welcome back, sir." rather than replaying initial onboarding greetings.
* **Sleep Mode Throttled Camera:** Camera runs at ~7 FPS (140ms intervals) in Sleep Mode for low-power emergency gesture wake detection (`open_palm → fist`).

---

## 11. Event Bus Wiring & Communication Matrix

All inter-module communication is asynchronous and non-blocking via [`event_bus`](file:///d:/Desktop/Code/personal/project/Jarvis_demo/auhip/core/event_bus.py):

* **Priority Levels:**
  * `EventPriority.CRITICAL`: `CANCEL_ALL`, `APP_EXIT`, `BARGE_IN`
  * `EventPriority.HIGH`: `SET_UI_MODE`, `ENTER_CAMERA_MODE`, `ENTER_CONTROL_MODE`, `EXIT_SUB_MODE`
  * `EventPriority.NORMAL`: Standard skills and intent execution
  * `EventPriority.LOW`: `LAST_COMMAND` preview labels, waveform updates, status tags
* **Thread-Safe Dispatching:** Subscriber lists are defensively copied during dispatching to prevent modification during iteration crashes.

---

## 12. ⌨️ Keyboard Shortcuts & Quick Reference

| Shortcut | Action |
|---|---|
| `Ctrl + Tab` or `F2` | Toggle between **Ambient Voice HUD** and **Developer Cockpit** |
| `Escape` | Stop listening / cancel current task / exit sub-mode |
| `Space` (when focused) | Push-to-talk |
| `Ctrl + K` | Global search pill in Cockpit |
| Click `[ 📖 User Guide ]` | Open interactive guide & shortcuts modal in Cockpit |

---

## 13. System Hardening & Audit Verification

The codebase has undergone a full system audit and hardening sweep documented in [`docs/SYSTEM_AUDIT.md`](file:///d:/Desktop/Code/personal/project/Jarvis_demo/docs/SYSTEM_AUDIT.md):

* **Windows DPI Awareness:** `qt.conf` configured with `WindowsArguments = dpiawareness=0` to eliminate `SetProcessDpiAwarenessContext()` Windows crashes.
* **Security Guardrails:** Path traversal blocked in `read_code_file` and `delete_file`; home directory removed from LLM sandbox; API keys moved to request headers.
* **Concurrency:** `Microphone._queues_lock` prevents thread collision; TTS uses thread-safe state lock; async tasks tracked with error callbacks.
* **Event Loop Cleanliness:** All deprecated `asyncio.get_event_loop()` calls replaced with `asyncio.get_running_loop()`.
* **Automated Verification:** 100% pass rate on `tests/test_audit_fixes.py` and `tests/test_polish_and_alignment.py`.

