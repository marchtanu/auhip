import asyncio
import logging
from typing import Dict, Any, Callable, Type
import time

logger = logging.getLogger(__name__)

class ServiceState:
    UNINITIALIZED = "UNINITIALIZED"
    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    IDLE = "IDLE"

class ManagedService:
    def __init__(self, name: str, factory: Callable[[], Any], idle_timeout: float = 300.0):
        self.name = name
        self.factory = factory
        self.idle_timeout = idle_timeout
        self.state = ServiceState.UNINITIALIZED
        self.instance = None
        self.last_used = 0.0
        self._lock = asyncio.Lock()

    async def get(self):
        """Retrieve the service instance, initializing it if necessary."""
        self.last_used = time.time()
        
        async with self._lock:
            if self.state == ServiceState.UNINITIALIZED or self.instance is None:
                logger.info(f"Lazy loading service: {self.name}")
                self.state = ServiceState.INITIALIZING
                
                # Check if factory is async or sync
                if asyncio.iscoroutinefunction(self.factory):
                    self.instance = await self.factory()
                else:
                    loop = asyncio.get_event_loop()
                    self.instance = await loop.run_in_executor(None, self.factory)
                    
                self.state = ServiceState.RUNNING
                logger.info(f"Service {self.name} is now RUNNING.")
                
            elif self.state == ServiceState.IDLE:
                self.state = ServiceState.RUNNING
                
            return self.instance

    async def check_idle(self):
        """Check if the service has exceeded its idle timeout and unload it if needed."""
        if self.state in [ServiceState.RUNNING, ServiceState.IDLE] and self.instance is not None:
            if time.time() - self.last_used > self.idle_timeout:
                logger.info(f"Service {self.name} has been idle for > {self.idle_timeout}s. Unloading to save RAM.")
                async with self._lock:
                    if hasattr(self.instance, 'stop'):
                        if asyncio.iscoroutinefunction(self.instance.stop):
                            await self.instance.stop()
                        else:
                            self.instance.stop()
                    elif hasattr(self.instance, 'close'):
                        if asyncio.iscoroutinefunction(self.instance.close):
                            await self.instance.close()
                        else:
                            self.instance.close()
                            
                    self.instance = None
                    self.state = ServiceState.UNINITIALIZED


class ServiceManager:
    """Manages lazy loading and resource cleanup of heavy subsystems."""
    def __init__(self):
        self._services: Dict[str, ManagedService] = {}
        self._monitor_task = None
        self._running = False

    def register(self, name: str, factory: Callable[[], Any], idle_timeout: float = 300.0):
        """Register a service factory with an idle timeout."""
        self._services[name] = ManagedService(name, factory, idle_timeout)
        logger.debug(f"Registered service: {name}")

    async def get(self, name: str) -> Any:
        """Get a service, instantiating it if it doesn't exist."""
        if name not in self._services:
            raise KeyError(f"Service {name} is not registered.")
        return await self._services[name].get()

    def start_monitor(self):
        """Start the background task to unload idle services."""
        if not self._running:
            self._running = True
            self._monitor_task = asyncio.create_task(self._monitor_loop())
            logger.info("ServiceManager background monitor started.")

    async def stop_monitor(self):
        """Stop the background monitor and unload all active services."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
                
        # Force cleanup
        for service in self._services.values():
            if service.instance is not None:
                await service.check_idle() # Trigger cleanup if possible or manual
                
        logger.info("ServiceManager stopped.")

    async def _monitor_loop(self):
        while self._running:
            try:
                await asyncio.sleep(10) # check every 10 seconds
                for service in self._services.values():
                    await service.check_idle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in ServiceManager monitor: {e}")

service_manager = ServiceManager()
