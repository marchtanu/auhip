import urllib.request
import json
import webbrowser
import urllib.parse
from datetime import datetime


async def tell_time() -> str:
    """Returns the current formatted time."""
    now = datetime.now().strftime("%I:%M %p")
    return f"The current time is {now}."


async def tell_date() -> str:
    """Returns the current date in a friendly format."""
    today = datetime.now().strftime("%A, %B %d, %Y")
    return f"Today is {today}."


async def search_web(query: str = "") -> str:
    """Searches the web for the given query."""
    if not query:
        return "What would you like me to search for?"

    encoded_query = urllib.parse.quote(query)
    url = f"https://www.google.com/search?q={encoded_query}"
    webbrowser.open(url)
    return f"Searching for '{query}' on Google."


async def get_weather(city: str = "") -> str:
    """
    Fetches current weather from wttr.in (no API key required).
    If city is blank, wttr.in auto-detects location from IP.
    """
    from auhip.core.config import config

    target = city.strip() or config.WEATHER_CITY.strip() or ""
    location = urllib.parse.quote(target) if target else ""
    url = f"https://wttr.in/{location}?format=j1"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "auhip/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        current = data["current_condition"][0]
        desc = current["weatherDesc"][0]["value"]
        temp_c = current["temp_C"]
        feels_c = current["FeelsLikeC"]
        humidity = current["humidity"]
        area = data["nearest_area"][0]["areaName"][0]["value"]
        country = data["nearest_area"][0]["country"][0]["value"]

        return (
            f"Weather in {area}, {country}: {desc}. "
            f"{temp_c}°C (feels like {feels_c}°C), humidity {humidity}%."
        )
    except Exception as e:
        return f"Could not fetch weather data right now: {str(e)}"


async def get_help() -> str:
    """Lists all available commands and their descriptions."""
    help_text = (
        "Available Commands:\n\n"
        "🔊 Audio Control:\n"
        " - Volume Up/Down: Adjust system volume\n"
        " - Mute: Toggle system audio mute\n\n"
        "ℹ️ Information:\n"
        " - Tell Time: Get current local time\n"
        " - Tell Date: Get today's date\n"
        " - Weather [city]: Current weather conditions\n"
        " - Status: Check CPU and RAM usage\n"
        " - Help: List all available commands\n\n"
        "⏱ Productivity:\n"
        " - Set Timer [duration]: e.g. 'set timer 5 minutes'\n"
        " - Add Task [description]: Add to task list\n"
        " - List Tasks: Show all tasks\n"
        " - Add Event [title] [date]: Add calendar event\n\n"
        "🌐 Navigation:\n"
        " - Open Browser: Launch default browser\n"
        " - Open [app]: Open app (notepad, calculator, explorer)\n"
        " - Search [query]: Search Google for something\n\n"
        "💻 System:\n"
        " - Sleep / Goodbye: Enter standby mode\n"
        " - Screenshot: Capture screen\n"
        " - Minimize: Minimize auhip window\n"
        " - Fullscreen: Toggle full screen mode\n\n"
        "👁️ Vision Control:\n"
        " - Vision On/Off: Toggle Camera Mode (Gestures)\n"
        " - Control On/Off: Toggle Control Mode (Cursor)\n"
        " - Eye Tracking On/Off: Toggle eye tracking\n"
        " - Hand Tracking On/Off: Toggle hand tracking\n"
        " - Two Hands / One Hand: Toggle multi-hand tracking"
    )
    return help_text
