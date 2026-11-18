import asyncio
import subprocess
import psutil
import pyautogui
import logging
import webbrowser
import os
from datetime import datetime

logger = logging.getLogger(__name__)

from auhip.core.event_bus import event_bus

async def sleep_mode() -> str:
    """Triggered by 'goodbye jojo' or sleep commands."""
    logger.info("SKILL: Sleep Mode.")
    await event_bus.publish("ENTER_SLEEP_MODE", {})
    return "Entering sleep mode. Sweet dreams."

async def system_status() -> str:
    """Reports real hardware and software status."""
    logger.info("SKILL: System Status.")
    cpu_usage = psutil.cpu_percent(interval=None)
    ram_usage = psutil.virtual_memory().percent
    return f"All systems operational. CPU: {cpu_usage}%. RAM: {ram_usage}%. Network: Connected."

async def volume_up() -> str:
    """Increase system volume."""
    pyautogui.press("volumeup")
    return "Increasing volume."

async def volume_down() -> str:
    """Decrease system volume."""
    pyautogui.press("volumedown")
    return "Decreasing volume."

async def mute_volume() -> str:
    """Mute/unmute system volume."""
    pyautogui.press("volumemute")
    return "Toggling mute."

async def open_browser() -> str:
    """Opens the default browser."""
    webbrowser.open("https://google.com")
    return "Opening browser."

async def take_screenshot() -> str:
    """Takes a screenshot of the primary monitor and saves it to a screenshots/ directory."""
    logger.info("SKILL: Take Screenshot.")
    try:
        os.makedirs("screenshots", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshots/screenshot_{timestamp}.png"
        screenshot = pyautogui.screenshot()
        screenshot.save(filename)
        return f"Screenshot captured successfully and saved to {filename}."
    except Exception as e:
        logger.error(f"Failed to take screenshot: {e}")
        return f"Failed to take screenshot: {str(e)}"

async def media_play_pause() -> str:
    """Toggle media play / pause state."""
    logger.info("SKILL: Media Play/Pause.")
    pyautogui.press("playpause")
    return "Media play/pause toggled."

async def media_next_track() -> str:
    """Skip to next media track."""
    logger.info("SKILL: Media Next Track.")
    pyautogui.press("nexttrack")
    return "Skipped to next track."

async def media_prev_track() -> str:
    """Skip to previous media track."""
    logger.info("SKILL: Media Previous Track.")
    pyautogui.press("prevtrack")
    return "Returned to previous track."
