# AUHIP Skills Registry

This document outlines all capabilities (tools) exposed to the LLM Brain and how to add new ones.

## Current Skills

### `home_automation.py`
- `activate_home_mode()`: Sets up the ambient workspace when the user arrives home.

### `system_controls.py`
- `sleep_mode()`: Puts the assistant to sleep.
- `system_status()`: Uses `psutil` to return real-time CPU and RAM percentages.
- `open_browser()`: Opens the system's default web browser.
- `volume_up()` / `volume_down()` / `mute_volume()`: Simulates media keys via `pyautogui`.
- `take_screenshot()`: Captures desktop screen.
- `media_play_pause()` / `media_next_track()` / `media_prev_track()`: Controls system media playback.

### `information.py`
- `tell_time()` / `tell_date()`: Returns the current system time and date formatted.
- `get_weather(city)`: Fetches weather data.
- `search_web(query)`: Takes a query argument and opens a search in the browser.
- `get_help()`: Returns a list of all available commands and descriptions.

### `productivity.py`
- `set_timer(duration)`: Starts an asynchronous countdown timer with audio chime.
- `open_app(app_name)`: Launches Windows applications.

### `organizer.py` (Workspace & Agentic Tools)
- `add_task(title)` / `list_tasks()` / `complete_task(id)`: To-do task organizer connected to `data/tasks.json`.
- `list_workspace_files()`: Lists files and folders in the workspace.
- `read_code_file(filename)`: Reads code file contents safely.
- `write_code_file(filename, content)`: Creates or overwrites code files.
- `patch_file(path, target, replacement)`: Replaces a specific snippet in a file.
- `view_directory_tree(path, max_depth)`: Generates an ASCII tree view of the workspace.
- `search_codebase(query, extension)`: Searches text patterns across code files.
- `run_powershell_guarded(command)`: Executes safe PowerShell commands with a 15-second timeout.
- `list_unused_files()`: Identifies unreferenced Python modules.
- `delete_file(filename)`: Guarded file deletion (protects core source files).
- `lookup_stock(ticker)`: Fetches financial ticker quotes.

### NotebookLM Tools
- `summarize_notebook(name)`: Generates executive briefings from documents in `user/notebooks/` and `docs/`.
- `generate_audio_overview(topic)`: Creates a 2-host AI podcast dialogue (Alex / Ryan & Taylor / Jenny).

### `youtube_music.py`
- `open_youtube_music()`: Launches YouTube Music in the default browser.
- `search_youtube_music(query)`: Searches and plays music on YouTube.

---

## How to Add a New Skill

1. **Write the Skill Function:**
   Create an `async def` function in `auhip/skills/<module>.py` with a descriptive docstring.
   ```python
   async def get_crypto_price(symbol: str) -> str:
       """Fetches real-time cryptocurrency price."""
       return f"The price of {symbol} is..."
   ```

2. **Export the Skill:**
   Add the function to `auhip/skills/__init__.py`.

3. **Register in Tool Registry:**
   `tool_registry.auto_discover("auhip.skills")` automatically registers it and extracts the JSON schema for Ollama and Gemini.

4. **Add Fast Path (Optional):**
   Add common voice trigger phrases to `_build_local_routes()` in `auhip/core/agent.py` for instant zero-latency execution.
