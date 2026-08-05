import asyncio
import logging
from typing import Callable, Dict, List, Any

logger = logging.getLogger(__name__)


class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, callback: Callable):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        logger.debug(f"Subscribed to {event_type}")

    def unsubscribe(self, event_type: str, callback: Callable):
        """Remove a specific callback from an event channel."""
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
                logger.debug(f"Unsubscribed from {event_type}")
            except ValueError:
                logger.warning(f"Callback not found for unsubscribe on {event_type}")

    async def publish(self, event_type: str, data: Any = None):
        if event_type in self._subscribers:
            tasks = []
            for callback in self._subscribers[event_type]:
                if asyncio.iscoroutinefunction(callback):
                    tasks.append(self._safe_invoke_async(callback, event_type, data))
                else:
                    self._safe_invoke_sync(callback, event_type, data)

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        logger.debug(f"Published {event_type}")

    async def _safe_invoke_async(self, callback: Callable, event_type: str, data: Any):
        """Execute an async subscriber with error isolation."""
        try:
            await callback(data)
        except Exception as e:
            logger.error(f"Subscriber error on '{event_type}' ({callback.__qualname__}): {e}", exc_info=True)

    def _safe_invoke_sync(self, callback: Callable, event_type: str, data: Any):
        """Execute a sync subscriber with error isolation."""
        try:
            callback(data)
        except Exception as e:
            logger.error(f"Sync subscriber error on '{event_type}' ({callback.__qualname__}): {e}", exc_info=True)


# Singleton instance
event_bus = EventBus()
