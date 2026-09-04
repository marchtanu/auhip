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
    patch_file, view_directory_tree, search_codebase, run_powershell_guarded,
    summarize_notebook, generate_audio_overview,
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

        # Build the local routing table — single source of truth from voice_commands
        self._local_routes = self._build_local_routes()

        # Derive the flat keyword set used by is_valid_command
        self._valid_keywords = self._build_valid_keywords()

        # Wire Supervisor and Planner agents for multi-step goals
        from auhip.core.agents.supervisor import SupervisorAgent
        from auhip.core.agents.planner import PlannerAgent
        from auhip.core.tool_registry import tool_registry
        tool_registry.set_tool_manager(self.tool_manager)
        self.supervisor = SupervisorAgent(self.router, self.tool_manager)
        self.planner = PlannerAgent(self.router, self.tool_manager)

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
        self.tool_manager.register_tool(
            ToolSchema(
                "patch_file",
                "Performs an exact string search-and-replace modification to a target file in the workspace.",
                parameters={
                    "path": {"type": "string", "description": "The workspace file path to modify."},
                    "target": {"type": "string", "description": "The exact substring to replace."},
                    "replacement": {"type": "string", "description": "The replacement content to insert."}
                },
                required=["path", "target", "replacement"]
            ),
            patch_file
        )
        self.tool_manager.register_tool(
            ToolSchema(
                "view_directory_tree",
                "Generates a formatted ASCII directory tree of the workspace up to a max depth.",
                parameters={
                    "path": {"type": "string", "description": "Root directory path (default: '.')."},
                    "max_depth": {"type": "integer", "description": "Maximum tree depth recursion (default: 3)."}
                }
            ),
            view_directory_tree
        )
        self.tool_manager.register_tool(
            ToolSchema(
                "search_codebase",
                "Searches for a text pattern or regex query across workspace code files.",
                parameters={
                    "query": {"type": "string", "description": "Search text pattern."},
                    "extension": {"type": "string", "description": "Optional file extension filter (e.g. '.py')."}
                },
                required=["query"]
            ),
            search_codebase
        )
        self.tool_manager.register_tool(
            ToolSchema(
                "run_powershell_guarded",
                "Executes a safe PowerShell command with security guardrails and execution timeout.",
                parameters={
                    "command": {"type": "string", "description": "The PowerShell command to run."}
                },
                required=["command"]
            ),
            run_powershell_guarded
        )
        self.tool_manager.register_tool(
            ToolSchema(
                "summarize_notebook",
                "Generates an executive briefing and summary from project notes and documentation.",
                parameters={
                    "name": {"type": "string", "description": "Optional project notebook or document name."}
                }
            ),
            summarize_notebook
        )
        self.tool_manager.register_tool(
            ToolSchema(
                "generate_audio_overview",
                "Generates a conversational dual-host audio overview dialogue (AI podcast).",
                parameters={
                    "topic": {"type": "string", "description": "Topic or focus of the audio overview."}
                }
            ),
            generate_audio_overview
        )

    # ── Mode ──────────────────────────────────────────────────────────────────

    def set_mode(self, mode: str):
        """Pass updated active context mode down to hybrid routing layer."""
        self.router.set_mode(mode)

    # ── Local Routing Table ───────────────────────────────────────────────────
    # Single source of truth: delegated to auhip.core.voice_commands

    def _build_local_routes(self) -> list:
        """Build the unified keyword → handler mapping from voice_commands."""
        from auhip.core.voice_commands import get_canonical_routes
        return get_canonical_routes()

    def _build_valid_keywords(self) -> set:
        """Derive the set of all valid keywords from voice_commands."""
        from auhip.core.voice_commands import build_valid_keywords
        return build_valid_keywords()

    # ── Command Execution ─────────────────────────────────────────────────────

    async def execute(self, user_text: str) -> str:
        """Route a transcribed voice command. Checks local skills first to minimise LLM usage."""

        # 1. Try local routing first to minimise latency
        local_response = await self._local_route(user_text)
        if local_response:
            logger.info(f"Local skill matched for: '{user_text}'")
            return local_response

        # 2. Check if complex goal requires Planner/Supervisor delegation
        text_lower = user_text.lower().strip()
        complex_keywords = ["plan", "workflow", "organize workspace", "create plan", "multi-step"]
        if any(kw in text_lower for kw in complex_keywords) and hasattr(self, 'supervisor') and self.supervisor:
            logger.info("Delegating complex multi-step goal to SupervisorAgent.")
            return await self.supervisor.process_goal(user_text)

        # 3. Dispatch to Hybrid LLM Router
        try:
            return await self.router.execute(user_text)
        except Exception as e:
            logger.error(f"Router core execution error: {e}")
            return "Error in neural orchestration layer. Please check logs."

    def is_valid_command(self, user_text: str) -> bool:
        """
        Check if the text contains any local skill keywords or wake words.
        Used by the speech fallback system to decide when to try Google Cloud.
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
        from auhip.core.voice_commands import dispatch_local_route
        return await dispatch_local_route(user_text)

