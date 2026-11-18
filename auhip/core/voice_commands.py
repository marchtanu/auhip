"""
auhip.core.voice_commands
-------------------------
Unified single source of truth for all voice command keyword mappings, mode transitions,
parameterised command parsers, and valid keywords list.

Used by both AuhipAgent and SupervisorAgent to prevent divergence across routing tables.
"""

import logging
import re
import inspect
from typing import List, Tuple, Callable, Any, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from auhip.core.llm.tool_manager import ToolManager

from auhip.core.event_bus import event_bus, EventPriority
from auhip.skills import (
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
    # Second Brain Operations (march_workspace)
    sync_workspace, get_acting_call_time, get_university_deadlines,
    get_financial_status, get_startup_sprint,
)

logger = logging.getLogger(__name__)


# ── Mode and Window Event Helpers ─────────────────────────────────────────────

async def switch_to_cockpit() -> str:
    """Switch user interface to Developer Cockpit."""
    await event_bus.publish("SET_UI_MODE", {"mode": "cockpit"}, priority=EventPriority.HIGH)
    return "Switching to Cockpit workspace."


async def switch_to_aesthetic() -> str:
    """Switch user interface to Ambient Voice HUD."""
    await event_bus.publish("SET_UI_MODE", {"mode": "aesthetic"}, priority=EventPriority.HIGH)
    return "Switching to Voice HUD."


async def vision_on() -> str:
    """Activate camera feed and gesture recognition."""
    await event_bus.publish("ENTER_CAMERA_MODE", {}, priority=EventPriority.HIGH)
    return "Entering camera mode."


async def vision_off() -> str:
    """Deactivate camera feed and return to voice mode."""
    await event_bus.publish("EXIT_SUB_MODE", {}, priority=EventPriority.HIGH)
    return "Exiting camera mode."


async def control_on() -> str:
    """Activate contactless Air-Mouse pointer control."""
    await event_bus.publish("ENTER_CONTROL_MODE", {}, priority=EventPriority.HIGH)
    return "Entering control mode."


async def control_off() -> str:
    """Deactivate Air-Mouse and return to voice mode."""
    await event_bus.publish("EXIT_SUB_MODE", {}, priority=EventPriority.HIGH)
    return "Exiting control mode."


async def exit_sub_mode() -> str:
    """Deactivate active sub-mode (camera or control) and return to voice HUD."""
    await event_bus.publish("EXIT_SUB_MODE", {}, priority=EventPriority.HIGH)
    return "Exiting mode."


async def toggle_fullscreen() -> str:
    """Toggle fullscreen window state."""
    await event_bus.publish("TOGGLE_FULLSCREEN", {})
    return "Toggling full screen mode."


async def minimize_window() -> str:
    """Minimize application window."""
    await event_bus.publish("MINIMIZE_WINDOW", {})
    return "Minimizing auhip window."


async def eye_on() -> str:
    """Activate eye and gaze tracking."""
    await event_bus.publish("SET_EYE_STATE", {"state": True})
    return "Eye tracking activated."


async def eye_off() -> str:
    """Deactivate eye tracking."""
    await event_bus.publish("SET_EYE_STATE", {"state": False})
    return "Eye tracking deactivated."


async def hand_on() -> str:
    """Activate hand tracking."""
    await event_bus.publish("SET_HAND_STATE", {"state": True})
    return "Hand tracking activated."


async def hand_off() -> str:
    """Deactivate hand tracking."""
    await event_bus.publish("SET_HAND_STATE", {"state": False})
    return "Hand tracking deactivated."


async def multi_hand_on() -> str:
    """Activate two-hand tracking."""
    await event_bus.publish("SET_MULTI_HAND", {"state": True})
    return "Two-hand tracking activated."


async def multi_hand_off() -> str:
    """Deactivate two-hand tracking."""
    await event_bus.publish("SET_MULTI_HAND", {"state": False})
    return "Single-hand tracking activated."


# ── Canonical Parameterless Route Table ───────────────────────────────────────

CANONICAL_ROUTES: List[Tuple[List[str], Callable]] = [
    # ── UI Mode Switching ──
    (["cockpit", "switch to cockpit", "open cockpit", "show workspace", "workspace mode", "cockpit mode"], switch_to_cockpit),
    (["voice hud", "switch to voice", "switch to voice mode", "aesthetic mode", "ambient mode", "orb mode", "voice mode"], switch_to_aesthetic),

    # ── System Controls ──
    (["volume up"], volume_up),
    (["volume down"], volume_down),
    (["mute"], mute_volume),
    (["open browser", "browser"], open_browser),
    (["sleep", "goodbye", "goodnight", "good night", "good bye", "goodbye jojo", "goodnight jojo"], sleep_mode),
    (["help", "commands"], get_help),
    (["screenshot", "take screenshot", "capture screen"], take_screenshot),

    # ── Information ──
    (["time", "what time"], tell_time),
    (["date", "today", "what day", "what's today", "what is today"], tell_date),
    (["status", "cpu", "ram"], system_status),

    # ── Second Brain Operations (march_workspace) ──
    (["sync workspace", "update workspace", "update my workspace", "recalibrate data", "sync data", "pull data"], sync_workspace),
    (["call time", "acting schedule", "next shoot", "next call time", "filming queue", "acting call"], get_acting_call_time),
    (["university deadlines", "homework due", "any homework", "academic status", "check deadlines", "moodle deadlines", "coursework due"], get_university_deadlines),
    (["financial status", "freelance status", "cash flow", "revenue status", "how much made", "monthly revenue"], get_financial_status),
    (["startup sprint", "stagelink sprint", "stagelink status", "startup status", "startup progress"], get_startup_sprint),

    # ── YouTube Music ──
    (["youtube music", "open music", "open youtube music"], open_youtube_music),

    # ── Media ──
    (["play music", "pause music", "play pause", "media play", "media pause", "toggle media"], media_play_pause),
    (["next track", "next song", "skip song", "skip track"], media_next_track),
    (["prev track", "prev song", "previous track", "previous song", "back track", "back song"], media_prev_track),

    # ── Camera / Vision mode ──
    (["vision up", "vison up", "camera up", "start camera", "turn on camera",
      "vision on", "activate vision", "open vision", "vision panel",
      "show vision", "open camera", "camera open", "camera mode", "vision mode"], vision_on),
    (["vision off", "vison off", "camera off", "stop camera", "turn off camera",
      "close vision", "deactivate vision", "hide vision", "close camera"], vision_off),

    # ── Eye tracking ──
    (["eyes up", "eye up", "eyes on", "eye on", "track eye", "track eyes",
      "activate eye", "start eye", "enable eye"], eye_on),
    (["eyes off", "eye off", "eyes down", "eye down",
      "stop eye", "deactivate eye", "disable eye"], eye_off),

    # ── Hand tracking ──
    (["hands up", "hand up", "hands on", "hand on", "track hand", "track hands",
      "activate hand", "start hand", "enable hand"], hand_on),
    (["hands down", "hand down", "hands off", "hand off",
      "stop hand", "deactivate hand", "disable hand"], hand_off),

    # ── Window controls ──
    (["full window", "full screen", "maximize window", "maximize"], toggle_fullscreen),
    (["minimize window", "minimize screen", "minimize"], minimize_window),

    # ── Control mode (Air-Mouse) ──
    (["control on", "control mode", "start control", "enable control",
      "cursor control", "cursor mode", "air mouse", "mouse control"], control_on),
    (["control off", "stop control", "disable control", "exit control",
      "exit control mode"], control_off),

    # ── Multi-hand ──
    (["two hands", "multi hand", "double hands", "activate two hand"], multi_hand_on),
    (["one hand", "single hand", "one hand track", "default hand"], multi_hand_off),

    # ── Sub-Mode Exit / Return to Voice HUD ──
    (["exit mode", "exit sub mode", "back to voice", "normal mode", "return to voice"], exit_sub_mode),

    # ── Organizer & Workspace (parameterless) ──
    (["list tasks", "todo list", "show tasks"], list_tasks),
    (["list calendar events", "list events", "calendar events", "upcoming events"], list_calendar_events),
    (["list workspace files", "list files", "show files"], list_workspace_files),
    (["list unused files", "find unused files", "unused files", "list unused"], list_unused_files),
    (["view directory tree", "directory tree", "project tree", "workspace tree"], view_directory_tree),
    (["summarize notebook", "briefing doc", "project briefing", "executive briefing"], summarize_notebook),
    (["audio overview", "deep dive podcast", "podcast overview", "ai podcast"], generate_audio_overview),
]


def get_canonical_routes() -> List[Tuple[List[str], Callable]]:
    """Returns the unified keyword-to-handler route list."""
    return CANONICAL_ROUTES


def build_valid_keywords() -> Set[str]:
    """
    Derives the complete set of valid keywords including parameterless macros
    and parameterised keywords. Used by is_valid_command().
    """
    keywords = set()
    for kw_list, _ in CANONICAL_ROUTES:
        keywords.update(kw_list)

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
        "patch file", "search codebase", "run command", "powershell",
        "remember", "save memory", "what did i decide", "find my memory",
        "show my memories", "forget this memory", "correct memory",
        "send to antigravity", "delegate to antigravity",
    ])
    return keywords


def _normalize_command(text: str) -> str:
    normalized = " ".join(text.lower().strip().rstrip(".!?").split())
    normalized = re.sub(r"^(?:please |can you |could you )", "", normalized)
    return re.sub(r",? (?:please|sir|jarvis|auhip)$", "", normalized)


async def _execute_skill(handler: Callable, arguments: dict, tool_manager: Optional["ToolManager"] = None) -> str:
    """Deterministic shortcuts use the same authorization boundary as LLM calls."""
    if handler.__module__ == __name__:
        return await handler(**arguments)
    if tool_manager is None:
        from auhip.core.tool_registry import tool_registry
        tool_manager = tool_registry._tool_manager
    if tool_manager is None:
        from auhip.core.llm.tool_manager import ToolManager
        from auhip.core.llm.types import ToolSchema
        tool_manager = ToolManager()
        types = {str: "string", int: "integer", float: "number", bool: "boolean"}
        parameters = {name: {"type": types.get(type(value), "string")}
                      for name, value in arguments.items()}
        tool_manager.register_tool(
            ToolSchema(handler.__name__, inspect.getdoc(handler) or handler.__name__,
                       parameters=parameters, required=list(arguments)), handler,
        )
    return await tool_manager.execute(handler.__name__, arguments)


async def dispatch_local_route(user_text: str, tool_manager: Optional["ToolManager"] = None) -> Optional[str]:
    """Parse arguments before matching complete parameterless command phrases."""
    text = _normalize_command(user_text)
    result = await dispatch_parameterised_route(text, user_text.strip(), tool_manager)
    if result is not None:
        return result
    aliases = {
        "what time is it": "time", "what is the time": "time", "what's the time": "time",
        "what is today's date": "date", "what is the date": "date", "what day is it": "date",
        "what's the date": "date", "what is the system status": "status",
    }
    text = aliases.get(text, text)
    for keywords, handler in CANONICAL_ROUTES:
        if text in keywords:
            return await _execute_skill(handler, {}, tool_manager)
    return None


async def dispatch_parameterised_route(text: str, original: str, tool_manager: Optional["ToolManager"] = None) -> Optional[str]:
    """Extract explicit command arguments without substring collisions."""
    async def execute(handler: Callable, arguments: dict) -> str:
        return await _execute_skill(handler, arguments, tool_manager)

    weather = re.fullmatch(
        r"(?:(?:what(?:'s| is)|tell me|check|show me)(?: the)? )?"
        r"(?:weather|forecast|temperature)(?: (?:in|for) (.+))?", text,
    )
    if weather:
        return await execute(get_weather, {"city": weather.group(1) or ""})

    timer = re.fullmatch(r"(?:(?:set|start) )?(?:a )?(?:timer|countdown)(?: for)?(?: (.*))?", text)
    if timer:
        return await execute(set_timer, {"duration_str": timer.group(1) or ""})

    # Preserve case and content in filenames, task titles, queries, and shell commands.
    # Normalized text is only used for recognizing the command prefix.
    parameter_routes = [
        (("search youtube music for ", "search youtube music ", "play music "), search_youtube_music, "query"),
        (("stock price of ", "lookup stock ", "check stock ", "stock "), lookup_stock, "ticker"),
        (("search github for ", "search github ", "github search "), search_github, "query"),
        (("add task ", "create task ", "new task "), add_task, "title"),
        (("read file ", "read code ", "open file ", "view file "), read_code_file, "filename"),
        (("delete file ", "remove file ", "delete code "), delete_file, "filename"),
        (("search codebase for ", "search codebase ", "search code for ", "search code "), search_codebase, "query"),
        (("run command ", "run powershell ", "powershell "), run_powershell_guarded, "command"),
    ]
    stripped_original = re.sub(r"^(?:please |can you |could you )", "", original, flags=re.IGNORECASE)
    for prefixes, handler, argument in parameter_routes:
        for prefix in prefixes:
            if text.startswith(prefix):
                value = stripped_original[len(prefix):].strip()
                if value:
                    if argument == "ticker":
                        value = value.split()[0].upper()
                    return await execute(handler, {argument: value})

    completion = re.fullmatch(r"(?:complete|finish) task (\d+)", text)
    if completion:
        return await execute(complete_task, {"index": int(completion.group(1))})

    for prefix in ("open ", "launch ", "start app "):
        if text.startswith(prefix):
            target = text[len(prefix):].strip()
            if target and target not in ("camera", "browser", "music", "youtube music", "cockpit", "vision"):
                return await execute(open_app, {"app_name": target})

    for prefix in ("search google for ", "search for ", "google ", "search "):
        if text.startswith(prefix):
            return await execute(search_web, {"query": stripped_original[len(prefix):].strip()})

    # Let the LLM parse actual dates instead of inventing tomorrow at 9 AM.
    return None
