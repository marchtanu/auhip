import asyncio
import logging
import os
import time

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    _HAS_WATCHDOG = True
except ImportError:
    Observer = None
    FileSystemEventHandler = object
    _HAS_WATCHDOG = False

from auhip.core.event_bus import event_bus, EventPriority

logger = logging.getLogger(__name__)

class WorkspaceEventHandler(FileSystemEventHandler):
    def __init__(self, loop):
        if _HAS_WATCHDOG:
            super().__init__()
        self.loop = loop
        self.supported_extensions = {
            ".txt", ".md", ".py", ".js", ".ts", ".json", ".csv"
        }

    def _should_index(self, path: str) -> bool:
        _, ext = os.path.splitext(path)
        return ext.lower() in self.supported_extensions

    def _trigger_index(self, path: str, action: str):
        if self._should_index(path):
            # Enqueue to event bus with BACKGROUND priority
            asyncio.run_coroutine_threadsafe(
                event_bus.publish(
                    "FILE_CHANGED", 
                    data={"path": path, "action": action},
                    priority=EventPriority.BACKGROUND
                ),
                self.loop
            )

    def on_created(self, event):
        if not event.is_directory:
            self._trigger_index(event.src_path, "created")

    def on_modified(self, event):
        if not event.is_directory:
            self._trigger_index(event.src_path, "modified")

    def on_deleted(self, event):
        if not event.is_directory:
            self._trigger_index(event.src_path, "deleted")

class WorkspaceIndexer:
    """
    Watches the workspace directory for file changes and incrementally
    indexes them into the Vector DB via the MemoryAgent.
    """
    def __init__(self, watch_dir: str = "."):
        self.watch_dir = os.path.abspath(watch_dir)
        self.observer = None
        
        # Subscribe to process background indexing tasks safely
        event_bus.subscribe("FILE_CHANGED", self._process_file_change)

    def start(self):
        if not _HAS_WATCHDOG:
            logger.info("watchdog not installed — workspace live file watcher disabled.")
            return
        if self.observer is None:
            loop = asyncio.get_running_loop()
            event_handler = WorkspaceEventHandler(loop)
            self.observer = Observer()
            self.observer.schedule(event_handler, self.watch_dir, recursive=True)
            self.observer.start()
            logger.info(f"WorkspaceIndexer started watching {self.watch_dir}")

    def stop(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            logger.info("WorkspaceIndexer stopped.")

    async def _process_file_change(self, data: dict):
        """Background task handler that reads the file and updates LanceDB."""
        from auhip.core.agents.memory import memory_agent
        
        path = data.get("path")
        action = data.get("action")
        
        if action in ["created", "modified"]:
            try:
                # Read file incrementally
                # A robust implementation would chunk the file using langchain splitters
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read(5000) # Read up to 5000 chars for now
                    
                if content.strip():
                    await memory_agent.add_long_term_memory(
                        text=content,
                        metadata={"source": path, "type": "file_chunk"}
                    )
                    logger.debug(f"Indexed updated file: {path}")
                    
            except Exception as e:
                logger.error(f"Failed to index file {path}: {e}")
        elif action == "deleted":
            # Remove from VectorDB if supported
            logger.debug(f"File deleted (needs DB purge): {path}")

indexer = WorkspaceIndexer()
