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
    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
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

    async def _handler(self, websocket: WebSocketServerProtocol, path: str = ""):
        logger.info(f"Client connected: {websocket.remote_address}")
        self.clients.add(websocket)
        try:
            async for message in websocket:
                await self._handle_client_message(message, websocket)
        except websockets.ConnectionClosed:
            logger.info(f"Client disconnected: {websocket.remote_address}")
        finally:
            self.clients.remove(websocket)

    async def _handle_client_message(self, message: str, websocket=None):
        """Accept only narrowly scoped local notification and goal messages."""
        try:
            data = json.loads(message)
            event_type = data.get("type")
            payload = data.get("payload", {})
            if not isinstance(payload, dict):
                raise ValueError("Payload must be an object.")

            if event_type == "AUHIP_NOTIFY":
                text = payload.get("text")
                if not isinstance(text, str) or not text.strip() or len(text) > 500:
                    raise ValueError("Notification text must contain 1 to 500 characters.")
                text = " ".join(text.split())
                await event_bus.publish(
                    "AUHIP_EXTERNAL_NOTIFICATION",
                    data={"text": text, "task_id": payload.get("task_id")},
                    priority=EventPriority.HIGH,
                )
            elif event_type == "PROCESS_GOAL":
                text = payload.get("text")
                if not isinstance(text, str) or not text.strip() or len(text) > 2000:
                    raise ValueError("Goal text must contain 1 to 2000 characters.")
                await event_bus.publish("PROCESS_GOAL", data={"text": text.strip()}, priority=EventPriority.HIGH)
            else:
                raise ValueError("Unsupported IPC message type.")

            if websocket is not None:
                await websocket.send(json.dumps({"ok": True, "accepted": event_type}))
        except Exception as e:
            logger.error(f"Failed to handle IPC message: {e}")
            if websocket is not None:
                try:
                    await websocket.send(json.dumps({"ok": False, "error": str(e)}))
                except websockets.ConnectionClosed:
                    pass

    async def _broadcast_event(self, event_type: str, payload: any):
        """Broadcasts an event bus message to all connected UI clients."""
        if event_type.startswith("TOOL_CONFIRMATION_"):
            return
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
