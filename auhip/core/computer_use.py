import logging
import asyncio
import os
import time
from typing import Dict, Any, List
import pyautogui
try:
    import uiautomation as auto
except ImportError:
    auto = None

from auhip.core.tool_registry import tool_registry, ToolSchema

logger = logging.getLogger(__name__)

# Configure PyAutoGUI for safety
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5 # Adds a slight delay between actions for realism

class ComputerActionLayer:
    """
    Provides deterministic and semantic primitives for controlling the host OS.
    Integrates with the PlannerAgent for execution and verification.
    """
    
    @staticmethod
    async def type_text(text: str, press_enter: bool = False) -> str:
        """Types text via the keyboard."""
        try:
            # We use run_in_executor because pyautogui blocks
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, pyautogui.write, text, 0.05)
            if press_enter:
                await loop.run_in_executor(None, pyautogui.press, 'enter')
            return f"Successfully typed: '{text[:20]}...'"
        except Exception as e:
            return f"Failed to type text: {e}"

    @staticmethod
    async def press_shortcut(keys: List[str]) -> str:
        """Presses a combination of keys (e.g. ['ctrl', 'c'])."""
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, lambda: pyautogui.hotkey(*keys))
            return f"Successfully pressed shortcut: {'+'.join(keys)}"
        except Exception as e:
            return f"Failed to press shortcut: {e}"

    @staticmethod
    async def click_at(x: int, y: int, button: str = "left", clicks: int = 1) -> str:
        """Clicks at specific screen coordinates."""
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, pyautogui.click, x, y, clicks, 0.2, button)
            return f"Clicked {button} at ({x}, {y}) {clicks} time(s)."
        except Exception as e:
            return f"Failed to click: {e}"
            
    @staticmethod
    async def get_active_window_title() -> str:
        """Returns the title of the currently focused window."""
        try:
            if auto:
                window = auto.GetForegroundControl()
                if window:
                    return f"Active Window: {window.Name}"
            return "Unable to determine active window."
        except Exception as e:
            return f"Failed to get active window: {e}"
            
    @staticmethod
    async def parse_desktop_dom() -> str:
        """
        Builds a semantic tree of the current active window using uiautomation.
        Returns a simplified JSON string representing buttons, inputs, and text.
        """
        if not auto:
            return "UIAutomation library not installed."
            
        try:
            loop = asyncio.get_running_loop()
            
            def _parse():
                window = auto.GetForegroundControl()
                if not window:
                    return "No active window."
                    
                elements = []
                # Walk the tree (shallow for performance)
                for item, depth in auto.WalkTree(window, maxDepth=3):
                    if item.Name and item.ControlTypeName in ['ButtonControl', 'EditControl', 'TextControl']:
                        rect = item.BoundingRectangle
                        elements.append({
                            "type": item.ControlTypeName.replace("Control", ""),
                            "name": item.Name,
                            "rect": [rect.left, rect.top, rect.right, rect.bottom]
                        })
                import json
                return json.dumps(elements, indent=2)
                
            result = await loop.run_in_executor(None, _parse)
            return result
        except Exception as e:
            return f"Failed to parse desktop DOM: {e}"

# Register these primitives into the Tool Registry so the Planner can use them
tool_registry.register(
    ToolSchema(
        name="type_text",
        description="Types text via the keyboard. Set press_enter=true to submit.",
        parameters={"type": "object", "properties": {
            "text": {"type": "string"},
            "press_enter": {"type": "boolean"}
        }},
        required=["text"]
    ),
    ComputerActionLayer.type_text
)

tool_registry.register(
    ToolSchema(
        name="press_shortcut",
        description="Presses a keyboard shortcut combination (e.g. ['ctrl', 'c']).",
        parameters={"type": "object", "properties": {
            "keys": {"type": "array", "items": {"type": "string"}}
        }},
        required=["keys"]
    ),
    ComputerActionLayer.press_shortcut
)

tool_registry.register(
    ToolSchema(
        name="get_active_window",
        description="Returns the title of the currently focused application window.",
    ),
    ComputerActionLayer.get_active_window_title
)

tool_registry.register(
    ToolSchema(
        name="parse_screen",
        description="Parses the active window and returns a JSON map of clickable buttons and text fields.",
    ),
    ComputerActionLayer.parse_desktop_dom
)
