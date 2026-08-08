import asyncio
import logging
from enum import IntEnum
from dataclasses import dataclass
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)

class EventPriority(IntEnum):
    CRITICAL = 0     # Wake words, emergency stops
    HIGH = 1         # Voice commands, GUI interactions
    NORMAL = 2       # standard LLM tasks
    LOW = 3          # Automation tasks
    BACKGROUND = 4   # Indexing, embedding generation

@dataclass
class PrioritizedEvent:
    priority: EventPriority
    event_type: str
    data: Any
    
    # Custom sort for the priority queue
    def __lt__(self, other: "PrioritizedEvent"):
        return self.priority < other.priority

class MultiQueueEventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._global_subscribers: List[Callable] = []
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running = False
        self._worker_task = None

    def subscribe(self, event_type: str, callback: Callable):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        logger.debug(f"Subscribed to {event_type}")

    def subscribe_all(self, callback: Callable):
        """Subscribe to ALL events. Callback must accept (event_type: str, data: Any)."""
        self._global_subscribers.append(callback)
        logger.debug("Added global subscriber.")

    def unsubscribe(self, event_type: str, callback: Callable):
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
                logger.debug(f"Unsubscribed from {event_type}")
            except ValueError:
                pass

    async def publish(self, event_type: str, data: Any = None, priority: EventPriority = EventPriority.NORMAL):
        """Enqueue an event with a specific priority."""
        event = PrioritizedEvent(priority=priority, event_type=event_type, data=data)
        await self._queue.put(event)
        logger.debug(f"Enqueued {event_type} at priority {priority.name}")

    def start(self):
        """Start the background worker to process events from the priority queue."""
        if not self._running:
            self._running = True
            self._worker_task = asyncio.create_task(self._process_queue())
            logger.info("MultiQueueEventBus started.")

    async def stop(self):
        """Stop processing new events and wait for the queue to drain if needed."""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            logger.info("MultiQueueEventBus stopped.")

    async def _process_queue(self):
        while self._running:
            try:
                event: PrioritizedEvent = await self._queue.get()
                await self._dispatch(event)
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing event queue: {e}", exc_info=True)

    async def _dispatch(self, event: PrioritizedEvent):
        """Invoke all subscribers for the given event."""
        tasks = []
        
        # Dispatch to specific subscribers
        if event.event_type in self._subscribers:
            for callback in self._subscribers[event.event_type]:
                if asyncio.iscoroutinefunction(callback):
                    tasks.append(self._safe_invoke_async(callback, event.event_type, event.data))
                else:
                    self._safe_invoke_sync(callback, event.event_type, event.data)
                    
        # Dispatch to global subscribers
        for callback in self._global_subscribers:
            if asyncio.iscoroutinefunction(callback):
                tasks.append(self._safe_invoke_global_async(callback, event.event_type, event.data))
            else:
                self._safe_invoke_global_sync(callback, event.event_type, event.data)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_invoke_async(self, callback: Callable, event_type: str, data: Any):
        try:
            await callback(data)
        except Exception as e:
            logger.error(f"Subscriber error on '{event_type}' ({callback.__qualname__}): {e}", exc_info=True)

    def _safe_invoke_sync(self, callback: Callable, event_type: str, data: Any):
        try:
            callback(data)
        except Exception as e:
            logger.error(f"Sync subscriber error on '{event_type}' ({callback.__qualname__}): {e}", exc_info=True)

    async def _safe_invoke_global_async(self, callback: Callable, event_type: str, data: Any):
        try:
            await callback(event_type, data)
        except Exception as e:
            logger.error(f"Global subscriber error on '{event_type}' ({callback.__qualname__}): {e}", exc_info=True)

    def _safe_invoke_global_sync(self, callback: Callable, event_type: str, data: Any):
        try:
            callback(event_type, data)
        except Exception as e:
            logger.error(f"Global sync subscriber error on '{event_type}' ({callback.__qualname__}): {e}", exc_info=True)

# Singleton instance replaces the old event_bus
event_bus = MultiQueueEventBus()
