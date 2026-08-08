import asyncio
import json
import logging
import websockets
from websockets.server import WebSocketServerProtocol
from typing import Set

from auhip.core.event_bus import event_bus, EventPriority

logger = logging.getLogger(__name__)

class IPCServer:
    """
    WebSocket Server for Inter-Process Communication between the Headless Daemon
    and the UI Client.
    """
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
        self.server = None

        # Subscribe globally to broadcast all events to clients
        event_bus.subscribe_all(self._broadcast_event)
    async def start(self):
        self.server = await websockets.serve(self._handler, self.host, self.port)
        logger.info(f"IPC Server running on ws://{self.host}:{self.port}")

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("IPC Server stopped.")

    async def _handler(self, websocket: WebSocketServerProtocol, path: str):
        logger.info(f"Client connected: {websocket.remote_address}")
        self.clients.add(websocket)
        try:
            async for message in websocket:
                await self._handle_client_message(message)
        except websockets.ConnectionClosed:
            logger.info(f"Client disconnected: {websocket.remote_address}")
        finally:
            self.clients.remove(websocket)

    async def _handle_client_message(self, message: str):
        """Parse incoming messages from the UI client and publish to the event bus."""
        try:
            data = json.loads(message)
            event_type = data.get("type")
            payload = data.get("payload", {})
            priority_val = data.get("priority", EventPriority.HIGH.value)
            
            if event_type:
                await event_bus.publish(
                    event_type, 
                    data=payload, 
                    priority=EventPriority(priority_val)
                )
        except Exception as e:
            logger.error(f"Failed to handle IPC message: {e}")

    async def _broadcast_event(self, event_type: str, payload: any):
        """Broadcasts an event bus message to all connected UI clients."""
        # We can optionally filter internal-only events here if they are too noisy.
        # But for now, we broadcast all to UI.
        self.broadcast_sync(event_type, payload)
    def broadcast_sync(self, event_type: str, payload: any):
        """Helper to broadcast formatted messages."""
        if not self.clients:
            return
            
        message = json.dumps({"type": event_type, "payload": payload})
        
        # websockets requires an async context to send
        async def _send():
            tasks = [asyncio.create_task(client.send(message)) for client in self.clients]
            await asyncio.gather(*tasks, return_exceptions=True)
            
        asyncio.create_task(_send())

ipc_server = IPCServer()
