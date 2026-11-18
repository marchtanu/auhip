# auhip AI Assistant — Mode Reference & Interaction Flow

> **Design Principle:** Only one primary interaction system dominates at a time — Voice, Camera, or Cursor Control. This prevents input conflicts, false triggers, and resource overload.

---

## State Hierarchy

```
STANDBY
├── [2 snaps + "daddy home"] ──→ VOICE MODE (Dual-Mode: Ambient Voice HUD or Cockpit)
│       ├── ["open camera" / "vision mode"] ──→ CAMERA MODE (Vision & Attention HUD)
│       ├── ["control on" / "air mouse"]   ──→ CONTROL MODE (Air-Mouse Pointer & Click)
│       └── [F2 or Ctrl+Tab]               ──→ TOGGLE VOICE HUD ⮀ COCKPIT
│
└── ["goodbye jojo" / "goodnight"] ──→ SLEEP MODE
        └── [2 snaps + "daddy home"] ──→ VOICE MODE

EMERGENCY (works in Sleep state)
└── [open_palm → fist] ──→ EXIT PROGRAM
```

---

## 🎨 Dual-Mode User Interface

### Mode A: Minimalist Atmospheric Voice HUD (`AmbientVoiceView`)
* **Aspect & Theme:** 16:9 full-screen desktop interface with a soft lavender, periwinkle, and pale blue atmospheric gradient.
* **Top Navigation Bar:** Floating frosted-glass bar at 75% screen width (`✦ auhip`, `v2.4 OS`, clock, `● Ready`, Cockpit switcher button, settings).
* **Center Status Indicator:** Dedicated status section with `Listening` / `Thinking` / `Speaking` / `Ready` and 3 pulsing dots.
* **Volumetric AI Orb:** 380–450px circular floating orb with 3-layer internal flowing plasma and liquid clouds.
* **Continuous Audio Waveform:** 92-bar symmetrical horizontal audio visualizer positioned behind the orb with louder peak clusters.
* **Transcription Feed:** Centered live speech text with pulsing indicator dot.

### Mode B: Modern Light-Mode Developer Cockpit (`CockpitView`)
* **Design Philosophy:** Built according to `docs/DESIGN.md` (warm stone/zinc palette, Inter typography, 8pt spatial grid).
* **Left Column:** System Status Card (FSM state, mic/TTS status, snap detection counter, CPU/RAM/GPU activity, and mini ambient gas orb).
* **Top Bento Cards:**
  * *Priorities Card:* Shows high-priority tasks. Click `View all tasks →` to launch the interactive Task Manager modal.
  * *In Progress Card:* Live project progress bar with direct link to Workspace Explorer.
  * *System Overview:* Local Ollama model status (`qwen2.5:7b`), VRAM allocation, and temperature.
* **Center Stack Deck (Switchable Workspaces):**
  1. `💬 Chat Workspace:` Complete conversational history, step execution checklist, and prompt input bar.
  2. `👁️ Vision & Air-Mouse HUD:` Live camera canvas, iris gaze telemetry, blink detection, and contactless Air-Mouse controls.
  3. `📁 Workspace Explorer:` File tree inspector, syntax-highlighted code viewer, and unused file scanner.
* **Right Column:** Command History (click any entry to immediately re-run) and Active Sub-Agents deck.
* **Bottom Drawer:** Collapsible Debug Controls, hardware overrides, mode switchers, and real-time event stream.
* **In-App Guide:** Interactive `[ 📖 User Guide & Shortcuts ]` modal detailing all gestures, commands, and layout features.

---

## Mode 1 — Standby

**Activated by:** `python main.py`

**Purpose:** Low-power passive listening. Ignores all voice commands and gestures except activation triggers. Camera and heavy AI models remain completely unloaded from RAM.

### Accepted Inputs

| Input | Action |
|---|---|
| Snap × 2 + **"daddy home"** | → Voice Mode |
| Snap × 2 + **"exit"** (exact) | → Shutdown (only from Sleep → Snap flow) |

---

## Mode 2 — Voice Mode

**Activated by:** 2 snaps + `"daddy home"` or `python main.py --direct`

**On Enter:** UI opens, always-listening voice recognition starts with continuous turn-taking and acoustic barge-in.

### Available Voice Commands

| Phrase(s) | Action |
|---|---|
| `"vision up"` / `"open camera"` / `"camera mode"` | → Activate Camera Mode |
| `"control on"` / `"control mode"` / `"air mouse"` | → Activate Air-Mouse Control Mode |
| `"cockpit"` / `"cockpit mode"` / `"open cockpit"` | → Switch UI to Developer Cockpit |
| `"voice mode"` / `"voice hud"` | → Switch UI to Ambient Voice HUD |
| `"goodbye jojo"` / `"goodnight"` | → Sleep Mode |
| `"help"` / `"commands"` | List all commands, modes, gestures |
| `"volume up"` / `"volume down"` / `"mute"` | Master volume control |
| `"time"` / `"what time"` / `"date"` | Read current time and date |
| `"status"` / `"cpu"` / `"ram"` | System resource report |
| `"browser"` / `"open browser"` | Open default browser |
| `"search [query]"` / `"google [query]"` | Web search |
| `"add task [title]"` | Add to-do task to organizer |
| `"list tasks"` / `"todo list"` | List active and completed tasks |
| `"complete task [id]"` | Mark task as completed |
| `"list workspace files"` / `"show workspace"` | List project directory files |
| `"view directory tree"` / `"directory tree"` | ASCII tree view of codebase |
| `"search codebase [query]"` | Search text pattern across project files |
| `"run command [powershell cmd]"` | Execute safe guarded PowerShell command |
| `"summarize notebook"` / `"executive briefing"` | Generate executive briefing from documents |
| `"audio overview"` / `"deep dive podcast"` | Generate dual-host AI podcast dialogue |
| `"check stock [ticker]"` | Real-time financial stock price lookup |
| `"play music [song]"` / `"open youtube music"` | Search and play YouTube Music |

---

## Mode 3 — Camera Mode

**Activated by:** voice command `"open camera"` from Voice Mode or clicking `[ 👁️ Vision ]` in Cockpit.

**On Enter:** Camera feed opens. Always-listening voice disabled.

### Camera Gestures

| Gesture | Action | Notes |
|---|---|---|
| **Thumb + Index + Middle up** | Volume Up | Hold to increase, shake upward to speed up |
| **Thumb + Index + Middle down** | Volume Down | Hold to decrease, shake downward to speed up |
| **Thumb + Index + Middle right** | Next Track | Point right |
| **Thumb + Index + Middle left** | Previous Track | Point left |
| **Open Palm → Fist** | Play / Pause | Must complete within 1.5s |
| **Index finger up only** | Temp voice ON | While held, speak any command |
| **Peace Sign (✌️ held 1.0s)** | Exit Camera Mode | Returns to Voice Mode |

---

## Mode 4 — Control Mode (Air-Mouse)

**Activated by:** voice command `"control on"` / `"air mouse"`, or clicking `[ 🎮 Enter Air-Mouse Mode ]` in Cockpit.

**On Enter:** Contactless mouse cursor control via 21-point hand tracking with sub-pixel 1€ filtering. Live target crosshair overlay rendered on the camera feed.

### Control Mode Gestures

| Gesture | Action | Notes |
|---|---|---|
| **Point Index Finger (☝️)** | Move Cursor | Cursor smoothly follows fingertip across the entire display |
| **Index + Thumb Pinch (🤏 <0.5s)** | Left Click | Brief pinch and release |
| **Index + Thumb Hold (🤏 ≥0.5s)** | Drag & Drop | `mouseDown` while held, `mouseUp` on release |
| **Double Pinch (🤏 twice in 0.4s)** | Double Click | Opens files, selects words |
| **Move Fist Up / Down (✊)** | Vertical Scroll | Scroll web pages and documents smoothly |
| **Rock Sign (🤘 Index + Pinky up)** | Exit Air-Mouse | Exits back to Voice Mode (1.5s cooldown) |

---

## Mode 5 — Sleep Mode

**Activated by:** `"goodbye jojo"` or `"goodnight"` from any active mode.

**Purpose:** Low-power standby. Camera hardware and MediaPipe models are unpowered to save battery.

### Accepted Inputs

| Input | Action |
|---|---|
| Snap × 2 + **"daddy home"** | → Voice Mode |
| Snap × 2 + **"exit"** | → Shutdown |
| `open_palm → fist` | → Exit program (global override) |

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl + Tab` or `F2` | Toggle between **Voice HUD** and **Cockpit Mode** |
| `Escape` | Stop listening / cancel current task / exit sub-mode |
| `Space` (when focused) | Push-to-talk |
| `Ctrl + K` | Global search pill in Cockpit |
