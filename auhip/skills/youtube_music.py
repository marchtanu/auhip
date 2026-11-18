"""
auhip YouTube Music skill.

Provides browser-based YouTube Music integration with no OAuth required:
  - open_youtube_music()          — open YouTube Music home
  - search_youtube_music(query)   — search and open a query in YouTube Music

Media playback control (play/pause, next, prev) is handled by the existing
system_controls media key skills which work globally across any media player.
"""

import webbrowser
import urllib.parse
import logging

logger = logging.getLogger(__name__)

_YTM_BASE = "https://music.youtube.com"


async def open_youtube_music() -> str:
    """Open YouTube Music in the default browser."""
    logger.info("SKILL: Opening YouTube Music.")
    webbrowser.open(_YTM_BASE)
    return "Opening YouTube Music."


async def search_youtube_music(query: str = "") -> str:
    """
    Search YouTube Music for a song, artist, album, or playlist.
    Opens the search results page directly in the default browser.
    """
    if not query:
        return "What would you like to search for on YouTube Music?"

    logger.info(f"SKILL: YouTube Music search -> '{query}'")
    encoded = urllib.parse.quote(query)
    url = f"{_YTM_BASE}/search?q={encoded}"
    webbrowser.open(url)
    return f"Searching YouTube Music for '{query}'."
