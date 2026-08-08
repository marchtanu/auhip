import logging
import json
from typing import Dict, Any, Optional
from auhip.core.event_bus import event_bus, EventPriority
from auhip.core.tool_registry import tool_registry

logger = logging.getLogger(__name__)

class SupervisorAgent:
    """
    The top-level orchestrator in the Agent Swarm.
    Receives user goals, decides whether it's a simple tool call, a local macro,
    or if it requires multi-step planning, and delegates to the appropriate specialist.
    """
    def __init__(self, llm_router):
        self.llm_router = llm_router
        self._local_routes = self._build_local_routes()
        logger.info("SupervisorAgent initialized.")

    def _build_local_routes(self) -> Dict[str, Any]:
        """Builds static routes that bypass the LLM for instantaneous execution."""
        # This mirrors the old agent's local routing but uses the new registry
        return {
            "daddy home": "activate_home_mode",
            "goodbye jojo": "sleep_mode",
            "open camera": "enter_camera_mode",
            "control on": "enter_control_mode",
        }

    async def process_goal(self, text: str) -> str:
        """Process a high-level goal from the user."""
        text_lower = text.lower().strip()
        
        # 1. Fast Path: Local Macros
        for trigger, tool_name in self._local_routes.items():
            if trigger in text_lower:
                logger.info(f"Supervisor triggering local route: {tool_name}")
                if tool_name.startswith("enter_"):
                    # Broadcast state change request
                    await event_bus.publish(tool_name.upper(), priority=EventPriority.HIGH)
                    return "Switching modes."
                else:
                    return await tool_registry.execute_in_sandbox(tool_name, {})

        # 2. Plan Generation Path
        # Determine if the prompt requires multi-step reasoning.
        # For AUHIP v2, we route complex tasks to the Planner Agent.
        complex_keywords = ["plan", "organize", "workflow", "extract", "report", "automate", "search workspace"]
        if any(kw in text_lower for kw in complex_keywords):
            logger.info("Supervisor delegating to PlannerAgent.")
            # We would invoke the PlannerAgent here.
            # For now, we simulate delegation.
            await event_bus.publish("DELEGATE_TO_PLANNER", data={"goal": text})
            return "Generating execution plan..."

        # 3. Standard Tool Routing Path (Fallback to HybridLLMRouter)
        logger.info("Supervisor delegating to LLM Router.")
        
        # We need to construct the prompt with the available tools
        schemas = tool_registry.get_all_schemas()
        
        try:
            # We assume router.route() returns a struct with tool_calls or text.
            response = await self.llm_router.route(text, schemas)
            
            # If response contains tool calls, execute them
            if hasattr(response, 'tool_calls') and response.tool_calls:
                results = []
                for call in response.tool_calls:
                    res = await tool_registry.execute_in_sandbox(call.name, call.arguments)
                    results.append(res)
                return "\n".join(results)
            else:
                return response.text if hasattr(response, 'text') else str(response)
                
        except Exception as e:
            logger.error(f"Supervisor LLM delegation failed: {e}")
            return "I encountered an error trying to process that."
