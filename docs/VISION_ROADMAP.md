# AUHIP: Next-Generation Agentic Assistant — Architecture & Specifications

> **System Vision:** A personal, local-first Jarvis blending autonomous agentic coding & document retrieval (Antigravity + Claude Cowork + Hermes Agent), OpenAI Advanced Voice-style conversational flow, a dual-mode UI (Aesthetic HUD vs. Functional Cockpit), hardware-optimized execution for the RTX 3060, and a 24/7 Railway Cloud Hub bridge.

---

## 🧭 Architecture Decision Record (ADR)

| Category | Decision | Architectural Rationale |
|---|---|---|
| **1. Agentic Core** | **Hybrid Voice & Chat with Live Cockpit** | Natural voice for quick commands and continuous dialogue; text prompt bar for code snippets; live file diffs and tool logs displayed in the Cockpit UI. |
| **2. Autonomy Level** | **Guarded Autonomy** | Auto-executes safe actions (reading files, workspace code edits, searches, testing); prompts for explicit confirmation only on dangerous actions (e.g. deletions, system configs, external pushes). |
| **3. Local Brain** | **Dynamic Dual-Brain Architecture** | `qwen2.5:7b` runs 100% in 6GB GPU VRAM for instant conversational voice (~50 t/s); spins up 14B coding model (or free Gemini Flash) dynamically for complex agentic workflows. |
| **4. UI Structure** | **Floating Ambient HUD + Full Dev Cockpit** | Mode A: Sleek, semi-transparent floating ambient HUD/orb with audio visualizer.<br>Mode B: Comprehensive developer cockpit with file tree, diff viewer, and terminal execution stream. Toggleable via UI button or voice. *(User providing visual references)*. |
| **5. Conversational Flow** | **OpenAI Voice-Style Turn-Taking & Barge-In** | Open conversational state without repeating wake words; instant barge-in audio cut-off when user speaks; proactive verbal updates when background agent tasks complete. |
| **6. Optimization** | **Smart Adaptive Throttling** | Camera & MediaPipe remain completely OFF unless gesture mode is active; event-driven audio callbacks; auto-unload heavy 14B models from VRAM 5 minutes after tasks finish. |
| **7. Deployment** | **Hybrid Local Desktop + Railway Cloud Hub** | Desktop client runs locally on Windows (RTX 3060, mic, local files, HUD/Cockpit); Railway hosts a 24/7 background agent hub for remote webhooks, background tasks, and remote chat when away from PC. |

---

## 🏗️ System Architecture Diagram

```text
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             WINDOWS LOCAL CLIENT (PC)                            │
│                                                                                  │
│   ┌────────────────────────────────┐         ┌───────────────────────────────┐   │
│   │     DUAL-MODE PYQT6 GUI        │         │        VOICE PIPELINE         │   │
│   │  [Aesthetic HUD] ⮀ [Cockpit]  │         │  - Vosk / Whisper STT         │   │
│   │  - Live Diffs   - File Tree    │         │  - Edge-TTS Streaming (Sound) │   │
│   │  - Ambient Orb  - Terminal     │         │  - Instant Barge-In Halt      │   │
│   └───────────────┬────────────────┘         └───────────────┬───────────────┘   │
│                   │                                          │                   │
│                   ▼                                          ▼                   │
│   ┌──────────────────────────────────────────────────────────────────────────┐   │
│   │                     AUHIP LOCAL AGENT ORCHESTRATOR                       │   │
│   │  - Finite State Machine (Continuous Voice Loop)                          │   │
│   │  - Guarded Autonomy Engine (Safe Workspace Tool Execution)               │   │
│   │  - Hardware Resource Manager (VRAM / Camera Throttling)                  │   │
│   └───────────────────────────────┬──────────────────────────────────────────┘   │
│                                   │                                              │
│                   ┌───────────────┴───────────────┐                              │
│                   ▼                               ▼                              │
│   ┌───────────────────────────────┐   ┌───────────────────────────────┐          │
│   │  LOCAL OLLAMA (RTX 3060)      │   │   LOCAL TOOL EXECUTION        │          │
│   │  - qwen2.5:7b (Hot in VRAM)   │   │   - Workspace file edit/patch │          │
│   │  - 14B / deepseek-r1 (On-dem) │   │   - PowerShell runner         │          │
│   └───────────────────────────────┘   └───────────────────────────────┘          │
└───────────────────────────────────┬──────────────────────────────────────────────┘
                                    │ WebSocket / REST Sync
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                         RAILWAY CLOUD AGENT HUB (24/7)                           │
│                                                                                  │
│   - Fast background tasks, cron triggers, cloud document storage                 │
│   - Remote Web / Telegram gateway to chat with Jarvis away from PC               │
│   - Gemini Cloud escalation bridge for massive context tasks                     │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Phased Execution Roadmap

### 🏁 Milestone 1: Conversational Voice Upgrade & Interruption (OpenAI Voice Mode)
- [x] Implement seamless barge-in: stop TTS audio stream instantly upon acoustic energy detection ([`auhip/audio/tts.py`](file:///d:/Desktop/Code/personal/project/Jarvis_demo/auhip/audio/tts.py)).
- [x] Implement continuous turn-taking conversation loop in `AuhipStateMachine` without requiring wake-words on every turn.
- [x] Switch local model configuration to `qwen2.5:7b` in [`auhip/core/config.py`](file:///d:/Desktop/Code/personal/project/Jarvis_demo/auhip/core/config.py).

### 🏁 Milestone 2: Agentic Coding Core (Hermes / Cowork Tooling)
- [x] Implement workspace agent tools: `patch_file`, `view_directory_tree`, `run_powershell_guarded`, `search_codebase` ([`auhip/skills/organizer.py`](file:///d:/Desktop/Code/personal/project/Jarvis_demo/auhip/skills/organizer.py)).
- [x] Build iterative ReAct / Agent loop: plan $\rightarrow$ execute tools $\rightarrow$ verify output $\rightarrow$ report back verbally ([`auhip/core/tool_registry.py`](file:///d:/Desktop/Code/personal/project/Jarvis_demo/auhip/core/tool_registry.py)).
- [x] Add guarded execution checks and confirmation flow for sensitive actions ([`auhip/skills/organizer.py`](file:///d:/Desktop/Code/personal/project/Jarvis_demo/auhip/skills/organizer.py)).

### 🏁 Milestone 3: Dual-Mode UI (Aesthetic HUD ⮀ Functional Cockpit)
- [x] Mode A (Aesthetic HUD): Minimal floating 16:9 full-screen interface, 380–450px volumetric AI orb with 3-layer internal flowing plasma and liquid clouds, symmetrical horizontal audio waveform, 75% frosted top nav, live speech transcription ([`auhip/gui/components/ambient_voice_view.py`](file:///d:/Desktop/Code/personal/project/Jarvis_demo/auhip/gui/components/ambient_voice_view.py)).
- [x] Mode B (Functional Cockpit): Light-mode developer workspace with System Status Card (mini orb), Bento Cards, center deck switcher (Chat, Vision & Air-Mouse HUD, Workspace Explorer), History, Active Tasks, Debug drawer, and in-app Guide modal ([`auhip/gui/components/cockpit/cockpit_view.py`](file:///d:/Desktop/Code/personal/project/Jarvis_demo/auhip/gui/components/cockpit/cockpit_view.py)).
- [x] Global hotkey (`Ctrl+Tab` or `F2`), voice command (`"cockpit"`, `"voice mode"`), and UI navigation toggles ([`auhip/gui/main_window.py`](file:///d:/Desktop/Code/personal/project/Jarvis_demo/auhip/gui/main_window.py)).

### 🏁 Milestone 4: Hardware Optimization
- [x] Camera on-demand: Completely disable OpenCV camera and unload MediaPipe models from RAM when not in camera/control mode (`CAMERA_ON_DEMAND = True` in [`auhip/vision/worker.py`](file:///d:/Desktop/Code/personal/project/Jarvis_demo/auhip/vision/worker.py)).
- [x] Memory lifecycle manager: Auto-unload heavy models from VRAM when idle; OneEuroFilter 1€ smoothing for responsive 30 FPS cursor tracking.

### 🏁 Milestone 5: Railway Cloud Hub
- [ ] Build lightweight FastAPI/WebSocket server deployable to Railway.
- [ ] Bi-directional sync between Windows Desktop client and Railway cloud instance.
