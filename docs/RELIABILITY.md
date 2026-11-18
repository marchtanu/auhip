# Reliability work — 18 November 2026

The current fixes address the release blockers found in the working-tree review:

- Application skills are no longer ignored by Git. Include the new `auhip/skills/*.py` files when committing this work; no private `user/`, `.env`, or `data/` files need to be committed.
- Typed cockpit commands, IPC goals, and voice commands share the state-machine/agent execution path. Explicit voice-mode controls now have a receiver, and overlapping typed commands are rejected while a command is active.
- Deterministic shortcuts execute tools through ToolManager. Sensitive names always require approval, and file mutation/shell/agent-dispatch handlers also enforce the granted context. Desktop-approved shell commands work without enabling the unattended bypass.
- Plans run as tracked tasks outside event dispatch. The dispatcher remains available for approvals and cancellation. Typed tool outcomes distinguish success, denial, and failure; dependent steps run only after success.
- Cancellation interrupts command and planner tasks and closes pending approval dialogs. Completed actions are not rolled back. Synchronous operating-system calls already in progress may finish; AUHIP reports this limitation instead of promising they were stopped.
- Timer parsing accepts the existing duration-string interface and no longer collides with time queries. Local command matching uses complete phrases so unrelated memory requests are not captured by date/time shortcuts.
- Classic voice is the default. Gemini Live requires `CLOUD_ENABLED=true` and explicit session audio-sharing approval; unattended-tool settings cannot bypass that approval. The standalone CLI requires `--accept-audio-sharing`. Cloud voice uses a generic prompt without hardcoded personal details or loaded local identity/memories.
- Live receives successive model turns, propagates disconnects, stops the other direction on stream failure, and releases microphone subscriptions, speaker streams, tasks, and its SDK client. The desktop and standalone CLI use the same implementation.
- The workspace explorer lets the user select the AUHIP project or second brain explicitly, and never mixes their relative file paths. Code search resolves result paths relative to the searched root, including workspaces on a different Windows drive.
- Older audit checks now resolve the checkout location instead of an obsolete machine-specific path. Mutation tests use temporary files and simulated approvals; external calls are simulated. The Google SDK, WebSocket, and MediaPipe dependencies are pinned to versions exercised locally.

## Verification

Run from the repository root:

```powershell
python main.py --help
python tests/run_local_checks.py
```

The release runner includes command delivery, concurrent submission, approve/deny/cancel behavior, dependency handling, timer routing, cloud/session consent, multi-turn Live reception and failure cleanup, workspace browsing, existing interface checks, and the earlier audit checks. It uses hidden Qt windows and does not need a microphone, camera, Ollama service, cloud credentials, or an external agent CLI. `.github/workflows/local-checks.yml` runs the same checks on Windows with Python 3.11.

Local result: **74 checks passed**. A temporary public-source snapshot without `.env`, `user/`, personal `data/`, or speech models also passed its release checks. Desktop and standalone Live help/startup imports passed in that snapshot, with classic voice verified as the configuration default. This used the installed dependencies, rather than a new package installation. Python syntax and Git whitespace checks passed.

Before distributing a build, also check real-device startup, snap/wake/sleep transitions, microphone switching, audible cancellation, camera gestures, and an explicitly approved Gemini Live session with several turns and a connection loss. These checks cannot be established by simulated unit tests. A fresh dependency installation and the hosted CI job must be verified in their respective environments.
