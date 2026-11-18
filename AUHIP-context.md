# AUHIP Shared Agent Context

This is the shared, human-readable context file for AI tools working on AUHIP. Read it before changing the project. Keep durable project decisions here; do not put secrets, credentials, personal records, or full task transcripts in this file.

## Product direction

AUHIP is intended to become a local-first personal second brain and hands-free work coordinator. It should capture goals and context, keep track of work over time, and let the user delegate complex implementation to coding agents such as Codex or Antigravity. AUHIP does not need to solve every coding task itself.

Local memory, voice, task tracking, and orchestration are the default. If a task is handed to a hosted AI, the prompt and selected project context leave the computer; make that handoff explicit and minimize the shared context.

## Current collaboration contract

- Coding agents read this file and the repository's applicable `AGENTS.md` / `.agents` guidance before acting.
- AUHIP creates a stable task ID when it dispatches to Antigravity. Other delegators should supply one; manual work can use a short generated ID.
- When the work ends, use the `auhip-handoff` skill to create a structured receipt and notify a running AUHIP instance.
- A receipt is a report from the coding agent, not proof that the change is correct. State checks honestly; use `not run` when no check was performed.
- Keep context updates short and durable. Put per-task details in the receipt, not here.
- Cloud inference is off by default. Even when enabled in settings, only a direct request for Gemini/cloud permits a cloud call; only that request is sent, not stored memories or prior turns.
- Personal facts, preferences, decisions, and projects are explicit curated memories. Conversation history, second-brain documents, project guidance, and agent receipts are separate sources and must not be mixed into personal-memory recall.

## Architecture facts

- Primary desktop entry point: `main.py` (PyQt6 + qasync).
- Cross-agent instructions: `.agents/skills/auhip-handoff/SKILL.md`.
- Task receipts: `.auhip/handoff/<task-id>.json` (local-only, Git-ignored).
- Curated memory data: `data/memory_records.json`; optional vector ranking uses a separate versioned LanceDB index. Legacy conversation records remain marked as history and are not automatically recalled.
- Second-brain notes live under `SECOND_BRAIN_PATH` and are searched as user-owned documents with source paths.
- Agent completion command: `python -m auhip.tools.handoff complete ...`; it saves the receipt and asks a running local AUHIP process to announce it.
- Antigravity dispatch: `send_to_antigravity` starts a confirmed, sandboxed Antigravity CLI task and expects the agent to submit the same handoff receipt when finished.
- Coordination: `auhip/core/state_machine.py` and `auhip/core/event_bus.py`.
- Agent and tools: `auhip/core/agent.py`, `auhip/core/llm/`, and `auhip/skills/`.
- Audio, vision, and UI live under `auhip/audio/`, `auhip/vision/`, and `auhip/gui/`.
- The daemon/client split is experimental. The desktop GUI is the primary runtime.
- Sensitive file edits/deletes and PowerShell execution require desktop approval. Do not bypass that guard unless the user explicitly asks for unattended execution.

## Durable decisions and updates

Add dated, concise notes below when a decision changes how agents should work. Prefer updating an existing note over duplicating it.

<!-- Shared agent context updates go below this line. -->

- 2026-11-18: Typed commands and IPC goals enter through the desktop state machine and share the agent/tool path with voice input. Deterministic tool shortcuts also use ToolManager; sensitive handlers require an approval context. Planner jobs run outside event dispatch and stop dependants on denied or failed outcomes. Cancellation targets command/planner jobs without claiming rollback.
- 2026-11-18: Classic voice is the default. Gemini Live requires the cloud master switch and explicit approval to share microphone audio and the session conversation; unattended-tool settings cannot grant that consent. Live uses a generic cloud prompt, without local identity files or saved memories. Desktop and standalone Live share one supervised, multi-turn audio engine.
