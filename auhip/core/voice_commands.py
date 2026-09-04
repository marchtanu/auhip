"""
auhip.core.voice_commands
-------------------------
Unified single source of truth for all voice command keyword mappings, mode transitions,
parameterised command parsers, and valid keywords list.

Used by both AuhipAgent and SupervisorAgent to prevent divergence across routing tables.
"""

import logging
from typing import List, Tuple, Callable, Any, Optional, Set

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
    ])
    return keywords


async def dispatch_local_route(user_text: str) -> Optional[str]:
    """
    Evaluates both parameterless and parameterised local commands.
    Returns response string if handled locally, or None if LLM reasoning is required.
    """
    text = user_text.lower().strip()

    # 1. Parameterless Routes
    for keywords, func in CANONICAL_ROUTES:
        if any(kw in text for kw in keywords):
            return await func()

    # 2. Parameterised Routes
    return await dispatch_parameterised_route(text, user_text)


async def dispatch_parameterised_route(text: str, original: str) -> Optional[str]:
    """Extract arguments and execute parameterised local skills."""
    # Weather
    if any(kw in text for kw in ("weather", "forecast", "temperature")):
        city = ""
        for kw in ("weather in", "forecast for", "temperature in", "weather"):
            if kw in text:
                city = text.split(kw, 1)[-1].strip()
                break
        return await get_weather(city)

    # Timer
    if any(kw in text for kw in ("timer", "countdown")):
        words = text.split()
        seconds = 0
        label = "Timer"
        for i, w in enumerate(words):
            if w.isdigit():
                val = int(w)
                unit = words[i + 1] if i + 1 < len(words) else "seconds"
                if "min" in unit:
                    seconds = val * 60
                elif "hour" in unit or "hr" in unit:
                    seconds = val * 3600
                else:
                    seconds = val
                break
        if seconds > 0:
            return await set_timer(seconds, label)

    # Launch Application
    if any(text.startswith(p) for p in ("open ", "launch ", "start app ")):
        for prefix in ("open ", "launch ", "start app "):
            if text.startswith(prefix):
                target = text[len(prefix):].strip()
                if target and target not in ("camera", "browser", "music", "youtube music", "cockpit", "vision"):
                    return await open_app(target)

    # YouTube Music Search
    if "search youtube music" in text or "play music" in text:
        for prefix in ("search youtube music for ", "search youtube music ", "play music "):
            if prefix in text:
                query = text.split(prefix, 1)[-1].strip()
                if query:
                    return await search_youtube_music(query)

    # Financial Stock Lookup
    if any(kw in text for kw in ("stock price of", "lookup stock", "check stock", "stock ")):
        for kw in ("stock price of ", "lookup stock ", "check stock ", "stock "):
            if kw in text:
                ticker = text.split(kw, 1)[-1].strip().split()[0].upper()
                if ticker:
                    return await lookup_stock(ticker)

    # GitHub Search
    if "search github" in text or "github search" in text:
        for kw in ("search github for ", "search github ", "github search "):
            if kw in text:
                q = text.split(kw, 1)[-1].strip()
                if q:
                    return await search_github(q)

    # Tasks
    if text.startswith("add task") or text.startswith("create task") or text.startswith("new task"):
        for prefix in ("add task ", "create task ", "new task "):
            if text.startswith(prefix):
                title = original[len(prefix):].strip()
                if title:
                    return await add_task(title)

    if text.startswith("complete task") or text.startswith("finish task"):
        for prefix in ("complete task ", "finish task "):
            if text.startswith(prefix):
                arg = text[len(prefix):].strip()
                for token in arg.split():
                    if token.isdigit():
                        return await complete_task(int(token))

    # Read file
    if any(text.startswith(p) for p in ("read file ", "read code ", "open file ", "view file ")):
        for prefix in ("read file ", "read code ", "open file ", "view file "):
            if text.startswith(prefix):
                fn = text[len(prefix):].strip()
                if fn:
                    return await read_code_file(fn)

    # Delete file
    if any(text.startswith(p) for p in ("delete file ", "remove file ", "delete code ")):
        for prefix in ("delete file ", "remove file ", "delete code "):
            if text.startswith(prefix):
                fn = text[len(prefix):].strip()
                if fn:
                    return await delete_file(fn)

    # Search Codebase
    if text.startswith("search codebase") or text.startswith("search code"):
        for prefix in ("search codebase for ", "search codebase ", "search code for ", "search code "):
            if text.startswith(prefix):
                query = original[len(prefix):].strip()
                if query:
                    return await search_codebase(query)

    # Run PowerShell
    if text.startswith("run command") or text.startswith("run powershell") or text.startswith("powershell "):
        for prefix in ("run command ", "run powershell ", "powershell "):
            if text.startswith(prefix):
                cmd = original[len(prefix):].strip()
                if cmd:
                    return await run_powershell_guarded(cmd)

    # Google / Web Search
    if any(text.startswith(p) for p in ("search google for ", "search for ", "google ", "search ")):
        for prefix in ("search google for ", "search for ", "google ", "search "):
            if text.startswith(prefix):
                q = original[len(prefix):].strip()
                if q:
                    return await search_web(q)

    # Calendar Event
    if text.startswith("add calendar event") or text.startswith("schedule event"):
        for prefix in ("add calendar event ", "schedule event "):
            if text.startswith(prefix):
                title = original[len(prefix):].strip()
                if title:
                    return await add_calendar_event(title, "tomorrow", "9:00 AM")

    return None
