import logging
import asyncio

logger = logging.getLogger(__name__)

async def activate_home_mode() -> str:
    """Triggered by 'daddy home'."""
    logger.info("SKILL: Home Mode activated.")
    await asyncio.sleep(0.5)
    return "Welcome home! I've prepared everything for you."
