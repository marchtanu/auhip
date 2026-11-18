"""
auhip productivity skills.

Provides:
  - set_timer(duration_str)  — natural-language async countdown timer
  - open_app(app_name)       — launch a named Windows application
"""

import asyncio
import subprocess
import logging
import re

logger = logging.getLogger(__name__)


# ── Timer ──────────────────────────────────────────────────────────────────────

def _parse_duration(duration_str: str) -> int | None:
    """
    Parse a natural-language duration into total seconds.
    Examples:
        "5 minutes"         -> 300
        "30 seconds"        -> 30
        "1 hour 30 minutes" -> 5400
        "2 mins 15 secs"    -> 135
    Returns None if no parseable unit is found.
    """
    duration_str = duration_str.lower()
    total = 0
    found = False

    patterns = [
        (r"(\d+)\s*(?:hour|hr)s?",   3600),
        (r"(\d+)\s*(?:minute|min)s?", 60),
        (r"(\d+)\s*(?:second|sec)s?",  1),
    ]
    for pattern, multiplier in patterns:
        match = re.search(pattern, duration_str)
        if match:
            total += int(match.group(1)) * multiplier
            found = True

    return total if found else None


async def set_timer(duration_str: str = "") -> str:
    """
    Start an asynchronous countdown timer.
    Natural-language duration accepted: '5 minutes', '30 seconds', '1 hour 10 minutes'.
    When the timer fires, publishes an AUHIP_RESPONSE event.
    """
    from auhip.core.event_bus import event_bus
    from auhip.core.config import config

    if not duration_str:
        return "Please specify a duration. For example: 'set timer 5 minutes'."

    seconds = _parse_duration(duration_str)
    if seconds is None or seconds <= 0:
        return (
            f"I couldn't understand '{duration_str}' as a duration. "
            "Try something like '5 minutes' or '30 seconds'."
        )

    # Format a human-friendly label for the confirmation
    parts = []
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h: parts.append(f"{h} hour{'s' if h != 1 else ''}")
    if m: parts.append(f"{m} minute{'s' if m != 1 else ''}")
    if s: parts.append(f"{s} second{'s' if s != 1 else ''}")
    label = " ".join(parts)

    logger.info(f"SKILL: Timer set for {seconds}s ({label}).")

    async def _fire():
        await asyncio.sleep(seconds)
        chime = "🔔 " if config.TIMER_CHIME else ""
        await event_bus.publish("AUHIP_RESPONSE", {
            "text": f"{chime}Timer done! {label} elapsed.",
            "type": "success",
        })
        logger.info(f"Timer fired after {seconds}s.")

    asyncio.create_task(_fire())
    return f"Timer set for {label}. I'll let you know when it's done."


# ── Open App ───────────────────────────────────────────────────────────────────

# Map friendly names to Windows executable names / shell commands
_APP_MAP: dict[str, str] = {
    # Common system apps
    "notepad":      "notepad.exe",
    "note":         "notepad.exe",
    "calculator":   "calc.exe",
    "calc":         "calc.exe",
    "explorer":     "explorer.exe",
    "file explorer": "explorer.exe",
    "files":        "explorer.exe",
    "paint":        "mspaint.exe",
    "task manager": "taskmgr.exe",
    "settings":     "ms-settings:",
    "camera":       "microsoft.windows.camera:",
    "calendar":     "outlookcal:",
    "mail":         "outlookmail:",
    "store":        "ms-windows-store:",
    "clock":        "ms-clock:",
    "maps":         "bingmaps:",
    "weather":      "bingweather:",
    "snipping":     "snippingtool.exe",
    "snip":         "snippingtool.exe",
    "cmd":          "cmd.exe",
    "terminal":     "wt.exe",
    "powershell":   "powershell.exe",
    "word":         "WINWORD.EXE",
    "excel":        "EXCEL.EXE",
    "powerpoint":   "POWERPNT.EXE",
    "chrome":       "chrome.exe",
    "firefox":      "firefox.exe",
    "edge":         "msedge.exe",
    "brave":        "brave.exe",
    "spotify":      "spotify.exe",
    "discord":      "discord.exe",
    "vscode":       "code",
    "vs code":      "code",
    "code":         "code",
}


async def open_app(app_name: str = "") -> str:
    """
    Launch a named Windows application by its friendly name.
    Supports: notepad, calculator, explorer, paint, task manager,
    settings, cmd, terminal, chrome, firefox, edge, spotify, discord, vscode, etc.
    """
    if not app_name:
        return "Please specify an app name. For example: 'open notepad'."

    key = app_name.strip().lower()

    # Try exact match first, then partial
    executable = _APP_MAP.get(key)
    if not executable:
        for alias, exe in _APP_MAP.items():
            if alias in key or key in alias:
                executable = exe
                break

    if not executable:
        return (
            f"I don't know how to open '{app_name}'. "
            "Try: notepad, calculator, explorer, chrome, spotify, terminal, etc."
        )

    try:
        logger.info(f"SKILL: Opening app '{app_name}' -> {executable}")
        # Use shell=True so ms-settings: URIs and similar work
        subprocess.Popen(executable, shell=True)
        return f"Opening {app_name.title()}."
    except Exception as e:
        logger.error(f"Failed to open app '{app_name}': {e}")
        return f"Couldn't open {app_name}: {str(e)}"
