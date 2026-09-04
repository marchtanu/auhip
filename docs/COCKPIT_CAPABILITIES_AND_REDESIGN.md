# auhip Cockpit UI Inventory & Full Capability Architecture

> **Purpose:** Master reference document detailing every visual component currently in **Cockpit Mode** and every capability of the **auhip** personal assistant. Serves as the blueprint for designing and implementing the next-generation user interface.

---

## 1. Executive Summary & Design Context

auhip is an agentic, local-first personal AI assistant built in Python with **PyQt6**, **qasync**, **Ollama**, **faster-whisper**, **Microsoft Edge-TTS**, and **MediaPipe**. 

The application provides a dual-mode visual interface:
1. **Aesthetic Voice HUD (Mode 0):** Minimalist, ChatGPT Voice-inspired interface featuring an ethereal volume-reactive 3D pastel gas orb, top status typography, and live speech transcription at the bottom.
2. **Developer Cockpit (Mode 1):** Full-featured desktop control center providing visual inspection and controls for vision tracking, code execution, system metrics, hardware toggles, and conversation logs.

---

## 2. Cockpit UI Inventory (Current Implementation)

Cockpit Mode is currently laid out as a 3-column desktop layout with a persistent top navigation bar and a collapsible bottom developer console:

```
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│  ✦ auhip v2.4 OS           [Last Command]           12:45    ● Ready   🌙    🎛️ Cockpit        │  <- Nav Bar (40px)
├──────────────────────┬──────────────────────────────────────────┬──────────────────────────────┤
│  LEFT PANEL (240px)  │  CENTER PANEL (Flexible Main Area)       │  RIGHT PANEL (240px)         │
│                      │                                          │                              │
│  • FSM State Badge   │  • Audio Waveform Card (80px height)     │  • Command History Card      │
│  • Mic Status Dot    │  • Vision Panel (Collapsible camera)     │    - Chronological list      │
│  • TTS Output Dot    │  • Live Transcript Card (User speech)    │    - Timestamps & responses  │
│  • Snap Detector     │  • auhip Response Card (Assistant text)  │  • Active Commands Card      │
│  • CPU % Gauge       │                                          │    - Ongoing timers/tasks    │
│  • RAM % Gauge       │                                          │                              │
├──────────────────────┴──────────────────────────────────────────┴──────────────────────────────┤
│  BOTTOM DEBUG PANEL (148px height — shown only in Cockpit Mode)                                │
│  [Hardware & Mic/TTS]  [Mode & Vision Switches]  [Prompt Bar & Tool Runner]  [Live Event Log] │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### Component Breakdown

#### A. Top Navigation Bar (`auhip/gui/components/nav_bar.py`)
* **Height:** Fixed `40px`, spans the entire top width.
* **Wordmark:** `✦ auhip` in bold typography.
* **Version Pill:** `v2.4 OS` pill badge.
* **Last Command Pill:** Centered dynamic badge showing the most recently executed tool or command.
* **Digital Clock:** Real-time digital clock (`HH:MM`) ticking every second via `QTimer`.
* **State Pill:** Real-time state dot and label (`● Standby`, `● Listening`, `● Speaking`).
* **Theme Switcher:** Circular pill button toggling between Light (off-white) and Dark (deep ink).
* **Mode Toggle Pill:** Pill button toggling between `🌌 Voice HUD` and `🎛️ Cockpit` (supports `Ctrl+Tab` or `F2`).

#### B. Left Column Panel (`auhip/gui/components/left_panel.py`)
* **Width:** Fixed `240px`.
* **State Badge (`StatePanel`):** Custom painted circular indicator showing current FSM state and status message.
* **Microphone Indicator:** Green/red dot showing microphone hardware capture state.
* **Voice Output (TTS) Indicator:** Green/red dot showing Edge-TTS audio playback state.
* **Snap Detector Indicator:** Two circle glyphs (`○ ○`) that light up sequentially upon acoustic peak detection (Snap 1 primes, Snap 2 triggers Voice Mode).
* **System Metrics Gauges:**
  * **CPU Utilization:** Dynamic horizontal progress bar + live percentage text (polled every 3s via `psutil`).
  * **RAM Utilization:** Dynamic horizontal progress bar + live percentage text.

#### C. Center Column Panel (`auhip/gui/components/center_panel.py`)
* **Width:** Stretches to fill available horizontal and vertical space.
* **Live Audio Waveform Card (`WaveformWidget`):** Fixed `80px` card visualizing incoming sound energy as dynamic vertical bars.
* **Collapsible Vision Panel (`VisionPanel`):**
  * Embedded OpenCV webcam frame.
  * Overlays MediaPipe landmark meshes (iris, gaze vector, facial mesh, hand skeleton).
  * FPS counter and gesture status badge.
  * `Calibrate` button for setting reference gaze coordinates.
* **Split Conversation View:**
  * **Left Card (`TranscriptPanel`):** Chronological chat bubbles showing timestamps and transcribed speech from the user.
  * **Right Card (`ResponsePanel`):** Formatted rich-text responses from auhip, including tool outputs, system alerts, and status banners.

#### D. Right Column Panel (`auhip/gui/components/right_panel.py`)
* **Width:** Fixed `240px`.
* **Command History Card (`HistoryPanel`):** Scrollable list of recent user requests, command execution status, and tool return previews.
* **Active Tasks Card (`ActiveCommandsPanel`):** Displays currently active background operations, timers, and scheduled jobs.

#### E. Developer Bottom Console (`DebugPanel`)
* **Height:** Fixed `148px`. Automatically **hidden in Voice Mode** and visible in Cockpit Mode.
* **Hardware & Audio Section:**
  * `Microphone enabled` checkbox.
  * `Voice output (TTS)` checkbox.
  * Camera device selector dropdown.
  * Microphone device selector dropdown.
* **Mode Override Buttons:** Direct trigger buttons to force state transitions: `[ Voice ]`, `[ Vision ]`, `[ Control ]`, `[ Sleep ]`.
* **Feature Toggles:**
  * `[ Eyes ]`: Toggle eye and gaze tracking.
  * `[ Hand ]`: Toggle single hand tracking.
  * `[ Multi ]`: Toggle two-hand tracking.
  * `[ Shutdown ]`: Trigger graceful exit sequence.
* **Manual Skill Runner:** Dropdown of all registered Python tools in the agent + `Run` button.
* **Direct Text Prompt Bar:** Text input field + `Send` button allowing the user to type queries directly without speaking.
* **Runtime Configuration:**
  * Wake phrase input field (default: `daddy home`) with `Apply` button.
  * TTS Voice selector dropdown (`RyanNeural`, `ChristopherNeural`, `GuyNeural`, `AriaNeural`, `JennyNeural`, `SAPI5 offline`) + `Test` voice button.
* **Live Event Log:** Embedded monospace terminal window streaming live event bus messages (`STATE_CHANGED`, `SPEECH_RECOGNIZED`, `COMMAND_EXECUTED`, etc.).

---

## 3. Full System Capability Matrix

### 3.1 Voice & Audio Subsystem
* **Speech-to-Text (STT):**
  * `faster-whisper` (`base` model on CPU with int8 quantization).
  * Voice Activity Detection (VAD) filter removing silent chunks.
  * Offline fallback to `VOSK` if whisper dependencies are unavailable.
* **Text-to-Speech (TTS):**
  * High-fidelity natural neural speech via `edge-tts` (`en-GB-RyanNeural`, `en-US-ChristopherNeural`, etc.).
  * 100% offline fallback via Windows SAPI5 (`pyttsx3`).
* **Instant Acoustic Barge-In:**
  * Real-time microphone RMS energy tracking during audio playback.
  * Instantly halts TTS audio within $\le 20\text{ms}$ when user voice is detected.
* **Continuous Turn-Taking:**
  * Open conversational loop allowing back-and-forth dialogue without repeating wake words.
  * Auto-standby on $15\text{s}$ silence timeout.
* **Acoustic Snap Detection:**
  * Bandpass-filtered peak audio detector enabling wake-up on finger snaps.

---

### 3.2 Vision & Computer Control Subsystem
* **Eye & Gaze Tracking:**
  * 468-point facial mesh + iris landmark detection.
  * Real-time gaze vector estimation and blink detection.
* **Hand Tracking & Gesture Recognition:**
  * MediaPipe 21-point 3D hand landmarks (single or dual-hand).
  * Gesture classification: Open palm, fist, pointing, peace sign, pinch, thumbs up.
* **Air-Mouse Computer Control (`CONTROL_MODE`):**
  * Control desktop mouse pointer using index fingertip coordinates.
  * Left-click via index-thumb pinch gesture.
* **Smart Hardware Gating:**
  * Camera and MediaPipe models are completely unloaded and shut off in Voice and Standby modes to eliminate hardware load and turn off the webcam light.

---

### 3.3 Brain, Reasoning & Tool Orchestration
* **Local LLM Engine:**
  * Connected to local `Ollama` daemon (`http://localhost:11434`).
  * Default brain: `qwen2.5:7b` (fits 100% in 6GB RTX 3060 VRAM).
  * Fallback brain: `qwen2.5:3b`.
* **Zero-Latency Keyword Router:**
  * Instant deterministic local routing table that bypasses LLM latency for standard commands (time, volume, browser, music, window management).
* **Multi-Turn Function Calling Loop:**
  * Structured tool schema definitions (`ToolSchema`).
  * Autonomous execution of Python functions with results synthesized back into conversational responses.

---

### 3.4 Complete Tool Catalog

| Category | Tool / Function | Signature & Description |
| :--- | :--- | :--- |
| **Agentic Coding** | `list_workspace_files` | Scans workspace directory tree and returns key project files. |
| | `read_code_file` | Reads and returns contents of any specified file in the workspace. |
| | `write_code_file` | Writes or overwrites code files with AI-generated implementations. |
| | `list_unused_files` | Scans Python codebase to detect orphaned modules not imported anywhere. |
| | `delete_file` | Deletes files securely with path validation preventing deletion of core modules. |
| **Developer Tools** | `search_github` | Searches GitHub repositories and code issues for a query. |
| | `lookup_stock` | Fetches real-time market data, price, and daily change for any ticker. |
| **Productivity** | `set_timer` | Sets an asynchronous background timer with audio/visual notification. |
| | `open_app` | Launches Windows apps (VS Code, Notepad, Calculator, Chrome, Spotify, etc.). |
| | `add_task` | Adds an item to the local persistent task list. |
| | `list_tasks` | Displays all pending and completed tasks. |
| | `complete_task` | Marks a task completed by index ID. |
| | `add_calendar_event` | Schedules an event with title, date, and time. |
| | `list_calendar_events` | Lists upcoming scheduled calendar events. |
| **Information** | `tell_time` | Returns formatted current local time. |
| | `tell_date` | Returns current full calendar date. |
| | `get_weather` | Fetches live weather conditions via wttr.in (auto-IP or city). |
| | `search_web` | Executes a Google search in the default web browser. |
| | `get_help` | Summarizes available voice commands and skills. |
| **System Controls** | `volume_up` | Increases system master volume by one step. |
| | `volume_down` | Decreases system master volume by one step. |
| | `mute_volume` | Toggles system audio mute. |
| | `open_browser` | Opens default web browser to a specified URL. |
| | `take_screenshot` | Captures full primary display and saves image to workspace. |
| | `system_status` | Returns live CPU %, RAM %, battery level, and system uptime. |
| | `sleep_mode` | Puts the assistant into low-power standby sleep. |
| **Media & Music** | `open_youtube_music` | Launches YouTube Music in the browser. |
| | `search_youtube_music` | Searches and plays a specific song or artist on YouTube Music. |
| | `media_play_pause` | Toggles system media playback (Play/Pause). |
| | `media_next_track` | Skips to next media track. |
| | `media_prev_track` | Rewinds to previous media track. |
| **Home Automation** | `activate_home_mode` | Triggers custom home automation routine and welcome greeting. |

---

## 4. UI Redesign Opportunities & Recommendations

The current Cockpit layout packs immense capability, but suffers from **2022-era dashboard fragmentation**:
- Split transcript on the left and response on the right forces users to look back and forth across two separate boxes.
- The prompt input bar is buried at the bottom of the developer debug panel.
- Fixed 240px sidebars take up nearly 500px of horizontal space even when idle.

### Proposed Redesign Architecture:

```
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│  ✦ auhip              [ 🌌 Voice HUD | 🎛️ Cockpit ]           12:45    ● Ready   🌙    ⚙️ Settings│  <- Editorial Top Nav
├─────────────────────────────────────────────────────────────┬──────────────────────────────────┤
│  UNIFIED CONVERSATION & CODE WORKSPACE                      │  COLLAPSIBLE INSPECTOR DRAWER    │
│                                                             │  [ Workspace | Tools | System ]  │
│  • Single unified conversation stream (ChatGPT / Claude)    │                                  │
│    - User speech bubbles (subtle ink outline)               │  [Tab: Workspace]                │
│    - auhip responses (rich markdown, code blocks, diffs)    │  • File tree & project files     │
│    - Tool execution pills (e.g. `✓ Read main.py`)           │  • Git status & code actions     │
│                                                             │                                  │
│  • Collapsible Vision HUD (floating picture-in-picture)     │  [Tab: Tools & Hardware]         │
│                                                             │  • Camera / Mic selectors        │
│  • Sleek Floating Command Bar at Bottom:                    │  • Vision toggles (Eyes, Hands)  │
│    ┌──────────────────────────────────────────────────────┐ │  • TTS voice selector & test     │
│    │ 💬 Type command or ask to code...        [🎙️] [⏎]    │ │                                  │
│    └──────────────────────────────────────────────────────┘ │  [Tab: System Metrics]           │
│                                                             │  • CPU & RAM gauges, Tasks       │
└─────────────────────────────────────────────────────────────┴──────────────────────────────────┘
```

### Aesthetic Principles for the New Design (`docs/DESIGN.md`):
1. **Editorial Print Palette:**
   - Canvas: Off-white `#F5F5F5` (`{colors.canvas}`) in day mode, deep ink `#0C0A09` in dark mode.
   - Text: Near-black ink `#0C0A09` for headings, `#4E4E4E` for running body.
   - Dividers: Subtle 1px hairlines `#E7E5E4` (`{colors.hairline}`).
2. **Typography Hierarchy:**
   - Display headings: **Weight 300 Light Serif** (Georgia / EB Garamond Light). Never bold.
   - UI elements, navigation, buttons: **Inter** at weight 400/500 with `+0.16px` letter-spacing.
3. **Geometry:**
   - Pill geometry (`border-radius: 9999px`) for all action buttons, search bars, and status tags.
   - Soft rounded cards (`border-radius: 16px`) for workspace panels.
