import logging
import json
from typing import Dict, Any, Optional
from auhip.core.event_bus import event_bus, EventPriority
from auhip.core.voice_commands import dispatch_local_route
from auhip.core.tool_registry import tool_registry

logger = logging.getLogger(__name__)

class SupervisorAgent:
    """
    The top-level orchestrator in the Agent Swarm.
    Receives user goals, decides whether it's a simple tool call, a local macro,
    or if it requires multi-step planning, and delegates to the appropriate specialist.
    """
    def __init__(self, llm_router, tool_manager=None):
        self.llm_router = llm_router
        self.tool_manager = tool_manager
        logger.info("SupervisorAgent initialized.")

    async def process_goal(self, text: str) -> str:
        """Process a high-level goal from the user."""
        text_lower = text.lower().strip()
        
        # 1. Fast Path: Local Macros & Canonical Routes
        local_res = await dispatch_local_route(text)
        if local_res:
            logger.info(f"Supervisor handled via local route: '{text}'")
            return local_res

        # 2. Plan Generation Path
        # Determine if the prompt requires multi-step reasoning.
        complex_keywords = ["plan", "organize", "workflow", "extract", "report", "automate", "search workspace"]
        if any(kw in text_lower for kw in complex_keywords):
            logger.info("Supervisor delegating to PlannerAgent.")
            await event_bus.publish("DELEGATE_TO_PLANNER", data={"goal": text})
            return "Generating execution plan..."

        # 3. Standard Tool Routing Path (Fallback to HybridLLMRouter)
        logger.info("Supervisor delegating to LLM Router.")
        try:
            response = await self.llm_router.execute(text)
            return response if response else "I couldn't generate a response."
        except Exception as e:
            logger.error(f"Supervisor LLM delegation failed: {e}")
            return "I encountered an error trying to process that."

