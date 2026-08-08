import sys
import logging
import asyncio
import json
import websockets
from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QAction, 
    QWidget, QVBoxLayout, QLineEdit, QListWidget, QLabel
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QTimer
import qasync

logger = logging.getLogger("auhip.client")
logging.basicConfig(level=logging.INFO)

class CommandPalette(QWidget):
    """
    A lightweight floating command palette for quick interaction with the AUHIP daemon.
    """
    def __init__(self, ws_client):
        super().__init__()
        self.ws_client = ws_client
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.resize(600, 400)
        # Center on screen (simplified)
        self.move(660, 300)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.container = QWidget(self)
        self.container.setStyleSheet("""
            QWidget {
                background-color: #1E1E1E;
                border-radius: 12px;
                border: 1px solid #333333;
                color: #FFFFFF;
                font-family: 'Inter', sans-serif;
            }
        """)
        
        inner_layout = QVBoxLayout(self.container)
        
        self.status_label = QLabel("AUHIP • Ready")
        self.status_label.setStyleSheet("color: #AAAAAA; font-size: 12px; border: none;")
        inner_layout.addWidget(self.status_label)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask AUHIP anything...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: #2D2D2D;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-size: 16px;
            }
        """)
        self.input_field.returnPressed.connect(self.submit_command)
        inner_layout.addWidget(self.input_field)
        
        self.results_list = QListWidget()
        self.results_list.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: transparent;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #333333;
            }
        """)
        inner_layout.addWidget(self.results_list)
        
        layout.addWidget(self.container)

    def submit_command(self):
        text = self.input_field.text().strip()
        if not text:
            return
            
        self.results_list.addItem(f"You: {text}")
        self.input_field.clear()
        self.status_label.setText("AUHIP • Thinking...")
        
        # Send to daemon
        if self.ws_client.connected:
            asyncio.create_task(self.ws_client.send_message("PROCESS_GOAL", {"text": text}))
        else:
            self.results_list.addItem("Error: Not connected to daemon.")

    def add_response(self, text: str):
        self.results_list.addItem(f"AUHIP: {text}")
        self.status_label.setText("AUHIP • Ready")
        self.results_list.scrollToBottom()

class WsClient:
    """Connects to the background AUHIP daemon via WebSockets."""
    def __init__(self):
        self.uri = "ws://localhost:8765"
        self.websocket = None
        self.connected = False
        self.palette = None

    def set_palette(self, palette: CommandPalette):
        self.palette = palette

    async def connect(self):
        try:
            self.websocket = await websockets.connect(self.uri)
            self.connected = True
            logger.info("Connected to AUHIP daemon.")
            if self.palette:
                self.palette.status_label.setText("AUHIP • Connected")
            await self._listen()
        except Exception as e:
            logger.error(f"Failed to connect to daemon: {e}")
            self.connected = False
            if self.palette:
                self.palette.status_label.setText("AUHIP • Disconnected")
            # Reconnect loop
            await asyncio.sleep(5)
            asyncio.create_task(self.connect())

    async def _listen(self):
        try:
            async for message in self.websocket:
                data = json.loads(message)
                event_type = data.get("type")
                payload = data.get("payload")
                
                if event_type == "AUHIP_RESPONSE" and self.palette:
                    self.palette.add_response(payload.get("text", str(payload)))
                elif event_type == "STATE_CHANGED" and self.palette:
                    state = payload.get("new_state", "")
                    self.palette.status_label.setText(f"AUHIP • {state}")
                    
        except websockets.ConnectionClosed:
            self.connected = False
            logger.info("Connection to daemon lost.")
            if self.palette:
                self.palette.status_label.setText("AUHIP • Disconnected")
            await asyncio.sleep(5)
            asyncio.create_task(self.connect())

    async def send_message(self, event_type: str, payload: dict):
        if self.connected and self.websocket:
            msg = json.dumps({"type": event_type, "payload": payload})
            await self.websocket.send(msg)

def create_systray(app, palette):
    tray_icon = QSystemTrayIcon(QIcon("auhip_icon.png"), app)
    tray_icon.setToolTip("AUHIP Executive OS")
    
    menu = QMenu()
    
    show_action = QAction("Show Command Palette")
    show_action.triggered.connect(lambda: palette.show() or palette.activateWindow() or palette.input_field.setFocus())
    menu.addAction(show_action)
    
    menu.addSeparator()
    
    quit_action = QAction("Quit AUHIP Client")
    quit_action.triggered.connect(app.quit)
    menu.addAction(quit_action)
    
    tray_icon.setContextMenu(menu)
    tray_icon.show()
    return tray_icon

async def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    ws_client = WsClient()
    palette = CommandPalette(ws_client)
    ws_client.set_palette(palette)
    
    # Hide initially
    palette.hide()
    
    tray = create_systray(app, palette)
    
    # Start WS connection
    asyncio.create_task(ws_client.connect())
    
    logger.info("AUHIP Client running in System Tray.")
    
    # Global hotkey listener would go here (e.g. using `keyboard` module)
    # For now, users can click the systray.

if __name__ == "__main__":
    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    with loop:
        loop.run_until_complete(main())
        loop.run_forever()
