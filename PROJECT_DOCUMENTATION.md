# AUHIP Project Documentation

The README is the maintained installation and configuration guide. This file records the architecture and operational limits in more detail.

## Runtime

`main.py` is the primary supported entry point. It creates the Qt application, audio devices, `AuhipAgent`, `AuhipStateMachine`, and `VisionWorker`, then connects them through `event_bus` under `qasync`.

```text
PyQt6 views ── event_bus ── AuhipStateMachine ── AuhipAgent
                                  │                    │
                         microphone / TTS        HybridLLMRouter
                         snap / camera           ToolManager → skills
```

The GUI is the primary desktop product. `auhip.daemon.main` and `auhip.client.main` implement an experimental split process via WebSockets. The split runtime does not yet have parity with the GUI runtime and should not be treated as a hosted service.

## Voice engines and network use

- `classic` uses the configured local speech recognition engine and the Ollama-backed LLM router. TTS is selected separately; Edge TTS requires network access, while `pyttsx3` is the local alternative.
- `gemini_live` uses Google's streaming voice API and requires a Gemini API key, `CLOUD_ENABLED=true`, and explicit session audio-sharing approval. It does not load saved memories or local identity files.
- LLM cloud escalation is controlled by `CLOUD_ENABLED`; both the code default and supplied `.env.example` disable it. Classic-mode cloud requests require an explicit user request for that turn.
- Whisper model weights may be downloaded on first use. Vosk can be selected as the offline recognizer when its model is installed.

Classic voice is the default in both code and the example configuration. The desktop uses classic mode when Live is disabled or its audio-sharing approval is denied.

## Tools and trust boundaries

`ToolManager` validates declared argument names and types, enforces execution timeouts, and checks absolute paths against configured roots using resolved path containment. Workspace file helpers independently resolve the target under the configured workspace root.

Workspace writes, patches, deletes, and arbitrary PowerShell are marked as sensitive. The desktop GUI prompts for approval on every call; headless mode denies them. `AUHIP_ALLOW_UNSAFE_TOOLS=true` bypasses approval and should not be used with unattended or untrusted inputs. PowerShell runs without a shell wrapper or execution-policy bypass, but an approved command still runs as the current user.

The planner validates generated tool names, unique step IDs, dependencies, and cycles before executing any steps. Its `verification_step` field remains descriptive metadata; the planner does not independently execute those natural-language verification instructions.

## Local state and distribution

Runtime personal data belongs outside public source distributions. `.gitignore` now ignores new files under `data/`, screenshots, logs, and Vosk model directories. Items already tracked by Git remain tracked until deliberately removed from the index; review `git ls-files data screenshots vosk-model-small-en-us-0.15` before publishing a repository snapshot.

Never commit `.env` or real API credentials. `.env.example` contains placeholders and local-first defaults.

## Cross-agent handoff

`AUHIP-context.md` is shared human-readable context for coding agents. The `auhip-handoff` project skill tells agents to read it and report task outcomes through `python -m auhip.tools.handoff`. Each task receives a separate JSON receipt under `.auhip/handoff/`, avoiding agents overwriting one shared structured file. The CLI notifies the loopback WebSocket service; the desktop app and daemon publish the message in the UI and speak it. If AUHIP is offline, the receipt is saved for later review but is not automatically announced at startup yet.
