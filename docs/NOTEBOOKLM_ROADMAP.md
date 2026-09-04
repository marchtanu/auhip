# AUHIP NotebookLM Capability Roadmap & Architecture

> **Objective:** Extend AUHIP to function as a private, local-first **NotebookLM** alternative, featuring document-grounded Q&A, automatic study guides/synthesis, and dual-host AI audio overviews (podcasts) using Edge-TTS neural voices.

---

## 🏛️ Core Architectural Pillars

```text
┌────────────────────────────────────────────────────────────────────────┐
│                          USER SOURCES / NOTEBOOKS                      │
│            (PDFs, Markdown notes, text files, code files, URLs)        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Ingestion & Chunking
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        LOCAL RETRIEVAL / EMBEDDINGS                    │
│        (nomic-embed-text via Ollama or in-memory vector index)         │
└───────────────────┬────────────────────────────────┬───────────────────┘
                    │ Grounded Context               │ Document Summary
                    ▼                                ▼
┌──────────────────────────────────────┐  ┌──────────────────────────────┐
│       GROUNDED Q&A WITH CITATIONS    │  │   SYNTHESIS & STUDY GUIDES   │
│   - Quotes specific pages/lines      │  │   - Executive Briefings      │
│   - Strict "no hallucination" guard  │  │   - FAQs & Study Flashcards  │
│   - Voice or text interface          │  │   - Chronological Timelines  │
└──────────────────────────────────────┘  └──────────────┬───────────────┘
                                                         │
                                                         ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   DUAL-HOST AUDIO OVERVIEW (PODCAST)                   │
│                                                                        │
│   Host 1 (Lead Analyst): en-GB-RyanNeural (British Jarvis persona)     │
│   Host 2 (Co-Host / Questioner): en-US-JennyNeural (US Female voice)   │
│                                                                        │
│   - Generates natural, turn-taking dialogue with banter & summaries    │
│   - Streams playback directly in RAM via sounddevice                   │
│   - Full audio player controls in PyQt6 GUI (Play, Pause, Scrub)       │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Implementation Phases & Current Status

### ✅ Phase 1: Notebook Ingestion & Document Grounding (Completed)
1. **Source Storage Directory:** Created `user/notebooks/` directory for local text and markdown files.
2. **Text Extraction:** Ingests documents and notes directly from `user/notebooks/` and `docs/`.
3. **Local Citations:** Ingests document snippets with file references and headers.

### ✅ Phase 2: Dual-Host Audio Overview ("Deep Dive Podcast") (Completed)
1. **Dialogue Script Generator:** Generates turn-taking conversational audio overview dialogue with two distinct personas:
   - **Host 1 (Alex / Jarvis):** Analytical, structured British voice (`en-GB-RyanNeural`).
   - **Host 2 (Taylor):** Inquisitive conversational US voice (`en-US-JennyNeural`).
2. **Skill Registration:** Triggered via voice (`"audio overview"`, `"deep dive podcast"`) or tool execution (`generate_audio_overview`).

### ✅ Phase 3: Synthesis & Study Guide Tools (Completed)
Registered in [`auhip/skills/organizer.py`](file:///d:/Desktop/Code/personal/project/Jarvis_demo/auhip/skills/organizer.py):
- `summarize_notebook(name: str)` — Generates executive briefing from indexed files.
- `generate_audio_overview(topic: str)` — Generates dual-host audio overview script.
- Parameterless voice triggers: `"summarize notebook"`, `"executive briefing"`, `"audio overview"`.

### 🔄 Phase 4: GUI Notebook Management Deck (In Progress)
- Integrated into Cockpit Center Deck under **📁 Workspace Explorer** for live file inspection, syntax rendering, and code scanning.

---

## 🔒 Privacy & Local Execution Guarantee
Unlike Google NotebookLM, which requires uploading proprietary documents to external cloud servers, AUHIP's NotebookLM mode operates **100% locally on your machine**:
- Local LLM via Ollama (`qwen2.5:7b` or `qwen2.5:14b`)
- Local embeddings via `nomic-embed-text`
- Local files stored directly in `user/notebooks/`
- Zero data transmission to third-party APIs
