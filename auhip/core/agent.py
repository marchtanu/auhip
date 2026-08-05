import os
import json
import logging
import asyncio
from typing import Dict, Callable, List, Tuple, Any, Optional

from dotenv import load_dotenv
import aiohttp

from auhip.skills import (
    # Home
    activate_home_mode,
    # System controls
    sleep_mode, system_status, open_browser,
    volume_up, volume_down, mute_volume,
    take_screenshot, media_play_pause,
    media_next_track, media_prev_track,
    # Information
    tell_time, tell_date, get_weather, search_web, get_help,
    # Productivity
    set_timer, open_app,
    # Organizer
    lookup_stock, search_github, add_task, list_tasks, complete_task,
    add_calendar_event, list_calendar_events,
    list_workspace_files, read_code_file, write_code_file,
    list_unused_files, delete_file,
    # YouTube Music
    open_youtube_music, search_youtube_music,
)

logger = logging.getLogger(__name__)

# Load env variables from .env file at project root
load_dotenv()


class AuhipAgent:
    """
    The hybrid local-first brain of AUHIP. Uses swappable local and cloud LLMs
    orchestrated through the HybridLLMRouter and centralized ToolManager.
    Tools are grouped into logical categories for maintainability.
    """

    def __init__(self):
        from auhip.core.llm import ContextManager, HybridLLMRouter, ToolManager, ToolSchema

        self.tool_manager = ToolManager()
        self.context_manager = ContextManager()
        self.router = HybridLLMRouter(self.tool_manager, self.context_manager)

        # Backward compatibility flag
        self.client = True

        # Register tools in logical groups
        self._register_all_tools()

        # Build the local routing table — single source of truth
        self._local_routes = self._build_local_routes()

        # Derive the flat keyword set used by is_valid_command
        self._valid_keywords = self._build_valid_keywords()

        logger.info("Hybrid local-first orchestration layer initialised.")

    @property
    def available_tools(self) -> dict:
        """Returns registered tools dict {name: handler} for legacy compatibility (e.g. DebugPanel)."""
        return {name: handler for name, (_, handler) in self.tool_manager._tools.items()}

    # ── Tool Registration ─────────────────────────────────────────────────────

    def _register_all_tools(self):
        """Orchestrator that registers all tools, grouped by category."""
        from auhip.core.llm import ToolSchema

        self._register_system_tools(ToolSchema)
        self._register_info_tools(ToolSchema)
        self._register_productivity_tools(ToolSchema)
        self._register_media_tools(ToolSchema)
        self._register_organizer_tools(ToolSchema)
        self._register_workspace_tools(ToolSchema)

    def _register_system_tools(self, ToolSchema):
        """Volume, browser, screenshot, system status, sleep."""
        self.tool_manager.register_tool(
            ToolSchema("activate_home_mode", "Run when the user arrives home. Sets the mood and confirms readiness."),
            activate_home_mode
        )
        self.tool_manager.register_tool(
            ToolSchema("sleep_mode", "Enter sleep/standby. Called when the user dismisses auhip for the night."),
            sleep_mode
        )
        self.tool_manager.register_tool(
            ToolSchema("system_status", "Return current CPU usage, RAM usage, and network status."),
            system_status
        )
        self.tool_manager.register_tool(
            ToolSchema("open_browser", "Open the system's default web browser."),
            open_browser
        )
        self.tool_manager.register_tool(
            ToolSchema("volume_up", "Increase system audio volume by one step."),
            volume_up
        )
        self.tool_manager.register_tool(
            ToolSchema("volume_down", "Decrease system audio volume by one step."),
            volume_down
        )
        self.tool_manager.register_tool(
            ToolSchema("mute_volume", "Toggle system audio mute."),
            mute_volume
        )
        self.tool_manager.register_tool(
            ToolSchema("take_screenshot", "Capture a screenshot of the primary screen and save it to the workspace."),
            take_screenshot
        )

    def _register_info_tools(self, ToolSchema):
        """Time, date, weather, web search, help."""
        self.tool_manager.register_tool(
            ToolSchema("tell_time", "Return the current local time."),
            tell_time
        )
        self.tool_manager.register_tool(
            ToolSchema("tell_date", "Return today's full date (day, month, year)."),
            tell_date
        )
        self.tool_manager.register_tool(
            ToolSchema(
                "get_weather",
                "Fetch current weather conditions for a city. Leaves city blank to auto-detect from IP.",
                parameters={"city": {"type": "string", "description": "City name. Leave blank to auto-detect."}},
                required=[]
            ),
            get_weather
        )
        self.tool_manager.register_tool(
            ToolSchema(
                "search_web",
                "Search Google for a query and open the results in the browser.",
                parameters={"query": {"type": "string", "description": "The search query string."}},
                required=["query"]
            ),
            search_web
        )
        self.tool_manager.register_tool(
            ToolSchema("get_help", "Lists all available commands and their descriptions."),
            get_help
        )

    def _register_productivity_tools(self, ToolSchema):
        """Timers, open apps."""
        self.tool_manager.register_tool(
            ToolSchema(
                "set_timer",
                "Start a countdown timer. Duration is a natural language string like '5 minutes' or '1 hour 30 seconds'.",
                parameters={"duration_str": {"type": "string", "description": "Natural language timer duration."}},
                required=["duration_str"]
            ),
            set_timer
        )
        self.tool_manager.register_tool(
            ToolSchema(
                "open_app",
                "Open a named Windows application such as notepad, calculator, chrome, spotify, terminal, vscode.",
                parameters={"app_name": {"type": "string", "description": "Friendly app name to open."}},
                required=["app_name"]
            ),
            open_app
        )

    def _register_media_tools(self, ToolSchema):
        """YouTube Music, media play/pause, track navigation."""
        self.tool_manager.register_tool(
            ToolSchema("open_youtube_music", "Open YouTube Music in the default browser."),
            open_youtube_music
        )
        self.tool_manager.register_tool(
            ToolSchema(
                "search_youtube_music",
                "Search YouTube Music for a song, artist, or album and open results in the browser.",
                parameters={"query": {"type": "string", "description": "Search query for YouTube Music."}},
                required=["query"]
            ),
            search_youtube_music
        )
        self.tool_manager.register_tool(
            ToolSchema("media_play_pause", "Toggle play/pause state for system media player."),
            media_play_pause
        )
        self.tool_manager.register_tool(
            ToolSchema("media_next_track", "Skip to the next media track."),
            media_next_track
        )
        self.tool_manager.register_tool(
            ToolSchema("media_prev_track", "Go back to the previous media track."),
            media_prev_track
        )

    def _register_organizer_tools(self, ToolSchema):
        """Tasks, calendar, stock, GitHub."""
        self.tool_manager.register_tool(
            ToolSchema(
                "lookup_stock",
                "Queries the real-time stock price of a given ticker symbol.",
                parameters={"ticker": {"type": "string", "description": "The stock ticker symbol (e.g. AAPL, MSFT, TSLA)."}},
                required=["ticker"]
            ),
            lookup_stock
        )
        self.tool_manager.register_tool(
            ToolSchema(
                "search_github",
                "Searches GitHub for a query.",
                parameters={
                    "query": {"type": "string", "description": "The search query."},
                    "search_type": {"type": "string", "description": "Category: repositories, issues, code, users."}
                },
                required=["query"]
            ),
            search_github
        )
        self.tool_manager.register_tool(
            ToolSchema(
                "add_task",
                "Adds a new task to the task list.",
                parameters={"title": {"type": "string", "description": "The task description."}},
                required=["title"]
            ),
            add_task
        )
        self.tool_manager.register_tool(
            ToolSchema("list_tasks", "Lists all active and completed tasks."),
            list_tasks
        )
        self.tool_manager.register_tool(
            ToolSchema(
                "complete_task",
                "Marks a task as completed based on its index ID.",
                parameters={"index": {"type": "integer", "description": "The 1-based index ID of the task to complete."}},
                required=["index"]
            ),
            complete_task
        )
        self.tool_manager.register_tool(
            ToolSchema(
                "add_calendar_event",
                "Adds a new event to the calendar.",
                parameters={
                    "title": {"type": "string", "description": "The event title."},
                    "date_str": {"type": "string", "description": "The date of the event (e.g. '2026-06-04' or 'tomorrow')."},
                    "time_str": {"type": "string", "description": "The time of the event (e.g. '9:00 AM' or '14:30')."}
                },
                required=["title", "date_str"]
            ),
            add_calendar_event
        )
        self.tool_manager.register_tool(
            ToolSchema("list_calendar_events", "Lists all upcoming calendar events."),
            list_calendar_events
        )

    def _register_workspace_tools(self, ToolSchema):
        """Code file operations, unused file detection."""
        self.tool_manager.register_tool(
            ToolSchema("list_workspace_files", "Lists key directories and files in the current coding workspace."),
            list_workspace_files
        )
        self.tool_manager.register_tool(
            ToolSchema(
                "read_code_file",
                "Reads a specific code file in the workspace and returns its contents.",
                parameters={"filename": {"type": "string", "description": "The name or path of the file to read."}},
                required=["filename"]
            ),
            read_code_file
        )
        self.tool_manager.register_tool(
            ToolSchema(
                "write_code_file",
                "Writes or overwrites a file in the workspace with specific code content.",
                parameters={
                    "filename": {"type": "string", "description": "The name or path of the file to write."},
                    "content": {"type": "string", "description": "The complete code content to write to the file."}
                },
                required=["filename", "content"]
            ),
            write_code_file
        )
        self.tool_manager.register_tool(
            ToolSchema("list_unused_files", "Scans the workspace to identify unused Python files (not imported anywhere)."),
            list_unused_files
        )
        self.tool_manager.register_tool(
            ToolSchema(
                "delete_file",
                "Deletes a file in the workspace securely, preventing deletion of core files.",
                parameters={"filename": {"type": "string", "description": "The name or path of the file to delete."}},
                required=["filename"]
            ),
            delete_file
        )

    # ── Mode ──────────────────────────────────────────────────────────────────

    def set_mode(self, mode: str):
        """Pass updated active context mode down to hybrid routing layer."""
        self.router.set_mode(mode)

    # ── Local Routing Table ───────────────────────────────────────────────────
    # Single source of truth: _build_local_routes returns the complete mapping.
    # is_valid_command is derived automatically so the two can never diverge.

    def _build_local_routes(self) -> list:
        """Build the unified keyword → handler mapping. This is the SINGLE SOURCE OF TRUTH."""
        from auhip.core.event_bus import event_bus

        # ── Vision / Mode event helpers ───────────────────────────────────────

        async def vision_on():
            await event_bus.publish("ENTER_CAMERA_MODE", {})
            return "Entering camera mode."

        async def vision_off():
            await event_bus.publish("EXIT_SUB_MODE", {})
            return "Exiting camera mode."

        async def toggle_fullscreen():
            await event_bus.publish("TOGGLE_FULLSCREEN", {})
            return "Toggling full screen mode."

        async def minimize_window():
            await event_bus.publish("MINIMIZE_WINDOW", {})
            return "Minimizing auhip window."

        async def eye_on():
            await event_bus.publish("SET_EYE_STATE", {"state": True})
            return "Eye tracking activated."

        async def eye_off():
            await event_bus.publish("SET_EYE_STATE", {"state": False})
            return "Eye tracking deactivated."

        async def hand_on():
            await event_bus.publish("SET_HAND_STATE", {"state": True})
            return "Hand tracking activated."

        async def hand_off():
            await event_bus.publish("SET_HAND_STATE", {"state": False})
            return "Hand tracking deactivated."

        async def control_on():
            await event_bus.publish("ENTER_CONTROL_MODE", {})
            return "Entering control mode."

        async def control_off():
            await event_bus.publish("EXIT_SUB_MODE", {})
            return "Exiting control mode."

        async def multi_hand_on():
            await event_bus.publish("SET_MULTI_HAND", {"state": True})
            return "Two-hand tracking activated."

        async def multi_hand_off():
            await event_bus.publish("SET_MULTI_HAND", {"state": False})
            return "Single-hand tracking activated."

        # ── Keyword → Function Mapping ────────────────────────────────────────
        # Grouped by category for easy maintenance.
        return [
            # ── System ──
            (["volume up"],                volume_up),
            (["volume down"],              volume_down),
            (["mute"],                     mute_volume),
            (["open browser", "browser"],  open_browser),
            (["sleep", "goodbye", "goodnight", "good night", "good bye",
              "goodbye jojo", "goodnight jojo"],         sleep_mode),
            (["help", "commands"],         get_help),
            (["screenshot", "take screenshot", "capture screen"], take_screenshot),

            # ── Information ──
            (["time", "what time"],        tell_time),
            (["date", "today", "what day", "what's today", "what is today"], tell_date),
            (["status", "cpu", "ram"],     system_status),

            # ── YouTube Music ──
            (["youtube music", "open music", "open youtube music"], open_youtube_music),

            # ── Media ──
            (["play music", "pause music", "play pause",
              "media play", "media pause", "toggle media"],  media_play_pause),
            (["next track", "next song", "skip song", "skip track"], media_next_track),
            (["prev track", "prev song", "previous track", "previous song",
              "back track", "back song"],                    media_prev_track),

            # ── Camera / Vision mode ──
            (["vision up", "vison up", "camera up", "start camera", "turn on camera",
              "vision on", "activate vision", "open vision", "vision panel",
              "show vision", "open camera", "camera open", "camera mode"], vision_on),
            (["vision off", "vison off", "camera off", "stop camera", "turn off camera",
              "close vision", "deactivate vision", "hide vision", "close camera"], vision_off),

            # ── Eye tracking ──
            (["eyes up", "eye up", "eyes on", "eye on", "track eye", "track eyes",
              "activate eye", "start eye", "enable eye"],    eye_on),
            (["eyes off", "eye off", "eyes down", "eye down",
              "stop eye", "deactivate eye", "disable eye"],  eye_off),

            # ── Hand tracking ──
            (["hands up", "hand up", "hands on", "hand on", "track hand", "track hands",
              "activate hand", "start hand", "enable hand"], hand_on),
            (["hands down", "hand down", "hands off", "hand off",
              "stop hand", "deactivate hand", "disable hand"], hand_off),

            # ── Window controls ──
            (["full window", "full screen", "maximize window", "maximize"], toggle_fullscreen),
            (["minimize window", "minimize screen", "minimize"],             minimize_window),

            # ── Control mode ──
            (["control on", "control mode", "start control",
              "enable control", "cursor control", "cursor mode"], control_on),
            (["control off", "stop control", "disable control",
              "exit control", "exit control mode"],              control_off),

            # ── Multi-hand ──
            (["two hands", "multi hand", "double hands", "activate two hand"], multi_hand_on),
            (["one hand", "single hand", "one hand track", "default hand"],    multi_hand_off),

            # ── Organizer (parameterless) ──
            (["list tasks", "todo list"],                list_tasks),
            (["list calendar events", "list events",
              "calendar events", "upcoming events"],     list_calendar_events),
            (["list workspace files", "list files", "show workspace"], list_workspace_files),
            (["list unused files", "find unused files",
              "unused files", "list unused"],            list_unused_files),
        ]

    def _build_valid_keywords(self) -> set:
        """Derive the set of all valid keywords from the local routing table.

        Also includes additional parameterised-route keywords and config phrases
        so is_valid_command is always in sync with _local_route.
        """
        keywords = set()

        # Pull all keywords from the parameterless route table
        for kw_list, _ in self._local_routes:
            keywords.update(kw_list)

        # Add parameterised route keywords (handled in _local_route_parameterised)
        keywords.update([
            "weather", "forecast", "temperature",
            "timer", "set timer", "set a timer", "countdown",
            "open ", "launch ", "start app",
            "search youtube music", "play music", "music",
            "search music", "search",
            "stock", "stock ", "lookup stock", "stock price",
            "ticker", "github", "search github",
            "add task", "complete task",
            "read file", "read code", "read ",
            "delete file", "remove file", "delete python file",
            "google",
            "calendar", "add event", "schedule",
        ])

        return keywords

    # ── Command Execution ─────────────────────────────────────────────────────

    async def execute(self, user_text: str) -> str:
        """Route a transcribed voice command. Checks local skills first to minimise LLM usage."""

        # 1. Try local routing first to minimise latency
        local_response = await self._local_route(user_text)
        if local_response:
            logger.info(f"Local skill matched for: '{user_text}'")
            return local_response

        # 2. Dispatch to Hybrid LLM Router
        try:
            return await self.router.execute(user_text)
        except Exception as e:
            logger.error(f"Router core execution error: {e}")
            return "Error in neural orchestration layer. Please check logs."

    def is_valid_command(self, user_text: str) -> bool:
        """
        Check if the text contains any local skill keywords or wake words.
        Used by the speech fallback system to decide when to try Google Cloud.

        Derived automatically from the same routing table as _local_route.
        """
        if not user_text:
            return False

        text = user_text.lower()

        if any(kw in text for kw in self._valid_keywords):
            return True

        # Check core config phrases
        from auhip.core.config import config
        if config.WAKE_PHRASE in text or config.EXIT_PHRASE in text or config.SHUTDOWN_PHRASE in text:
            return True

        return False

    async def _local_route(self, user_text: str):
        """Local keyword dispatch to bypass LLM for common and well-known commands."""
        text = user_text.lower()

        # ── Parameterless routes (from the unified mapping) ───────────────────
        for keywords, func in self._local_routes:
            if any(kw in text for kw in keywords):
                return await func()

        # ── Parameterised routes ──────────────────────────────────────────────
        return await self._local_route_parameterised(text, user_text)

    async def _local_route_parameterised(self, text: str, original: str):
        """Handle commands that need argument extraction from the text."""

        # Weather: "weather", "weather in [city]", "forecast"
        if any(kw in text for kw in ("weather", "forecast", "temperature")):
            city = ""
            for kw in ("weather in", "forecast for", "temperature in", "weather"):
                if kw in text:
                    city = text.split(kw, 1)[-1].strip()
                    break
            return await get_weather(city)

        # Timer: "set a timer for 5 minutes", "timer 30 seconds"
        if any(kw in text for kw in ("timer", "set timer", "set a timer", "countdown")):
            duration = ""
            for kw in ("set a timer for", "set timer for", "set a timer", "set timer", "timer for", "timer"):
                if kw in text:
                    duration = text.split(kw, 1)[-1].strip()
                    break
            return await set_timer(duration)

        # Open app: "open notepad", "launch calculator", "start terminal"
        if any(kw in text for kw in ("open ", "launch ", "start app")):
            for kw in ("launch", "open"):
                if kw in text:
                    app = text.split(kw, 1)[-1].strip()
                    # Exclude substrings that are handled by other routes
                    excluded = {"browser", "camera", "music", "youtube music", "vision"}
                    if app and app not in excluded and not any(e in app for e in excluded):
                        return await open_app(app)

        # YouTube Music search: "search youtube music for [query]", "play [query] on youtube music"
        if "youtube music" in text or ("music" in text and "search" in text):
            for kw in ("search youtube music for", "search youtube music", "play on youtube music",
                       "search music for", "play music"):
                if kw in text:
                    query = text.split(kw, 1)[-1].strip()
                    if query:
                        return await search_youtube_music(query)
            # Bare "youtube music" with something after it
            if "youtube music" in text:
                q = text.split("youtube music", 1)[-1].strip()
                if q:
                    return await search_youtube_music(q)

        # Stock: "stock AAPL", "lookup stock MSFT"
        if any(kw in text for kw in ("stock ", "lookup stock ", "stock price ")):
            for kw in ("lookup stock", "stock price", "stock"):
                if kw in text:
                    ticker = text.split(kw, 1)[-1].strip()
                    if ticker:
                        return await lookup_stock(ticker)

        # GitHub search
        if "github" in text:
            for kw in ("search github for", "search github", "github search", "github"):
                if kw in text:
                    query = text.split(kw, 1)[-1].strip()
                    if query:
                        return await search_github(query)

        # Task management
        if "add task" in text:
            title = text.split("add task", 1)[-1].strip()
            if title:
                return await add_task(title)

        if "complete task" in text:
            idx_str = text.split("complete task", 1)[-1].strip()
            if idx_str:
                return await complete_task(idx_str)

        # File read
        if any(kw in text for kw in ("read file ", "read code ", "read ")):
            for kw in ("read file", "read code", "read"):
                if kw in text:
                    filename = text.split(kw, 1)[-1].strip()
                    if filename and filename not in ("browser", "fullscreen", "minimize", "help"):
                        return await read_code_file(filename)

        # File delete
        if any(kw in text for kw in ("delete file ", "remove file ", "delete python file ")):
            for kw in ("delete file", "remove file", "delete python file"):
                if kw in text:
                    filename = text.split(kw, 1)[-1].strip()
                    if filename:
                        return await delete_file(filename)

        # Web search (last — very broad)
        if "search" in text or "google" in text:
            for kw in ("search for", "search", "google"):
                if kw in text:
                    query = text.split(kw, 1)[-1].strip()
                    if query:
                        return await search_web(query)

        return None

