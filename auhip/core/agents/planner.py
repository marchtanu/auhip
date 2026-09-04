import logging
import json
import asyncio
from typing import List, Dict, Any
from pydantic import BaseModel, Field

from auhip.core.event_bus import event_bus
from auhip.core.tool_registry import tool_registry

logger = logging.getLogger(__name__)

class ActionNode(BaseModel):
    id: str
    tool_name: str
    arguments: Dict[str, Any]
    dependencies: List[str] = Field(default_factory=list)
    verification_step: str = ""

class ActionGraph(BaseModel):
    nodes: List[ActionNode]
    goal: str

class PlannerAgent:
    """
    Generates Acyclic Action Graphs for multi-step goals.
    Provides execution, verification, and rollback tracking.
    """
    def __init__(self, llm_router, tool_manager=None):
        self.llm_router = llm_router
        self.tool_manager = tool_manager
        event_bus.subscribe("DELEGATE_TO_PLANNER", self.handle_planning_request)
        logger.info("PlannerAgent initialized.")

    async def handle_planning_request(self, payload: dict):
        """Event handler when the Supervisor delegates a goal."""
        goal = payload.get("goal")
        if not goal:
            return
            
        logger.info(f"PlannerAgent received goal: {goal}")
        
        # 1. Generate Plan
        graph = await self.generate_plan(goal)
        
        if graph:
            # 2. Execute Plan
            await self.execute_plan(graph)
            
    async def generate_plan(self, goal: str) -> ActionGraph:
        """Uses the LLM to convert a goal into an ActionGraph."""
        if self.tool_manager:
            schemas = [s.to_dict() if hasattr(s, "to_dict") else s for s in self.tool_manager.get_schemas()]
        else:
            schemas = tool_registry.get_all_schemas()
        
        prompt = (
            f"Goal: {goal}\n"
            "Create a multi-step action plan using the available tools. "
            "Output MUST be valid JSON matching the ActionGraph schema: "
            "{'goal': '...', 'nodes': [{'id': 'step1', 'tool_name': '...', 'arguments': {}, 'dependencies': [], 'verification_step': '...'}]}"
        )
        
        try:
            # Enforce JSON mode via the router
            response = await self.llm_router.generate_json(prompt, schemas)
            
            # Parse the JSON into our Pydantic model
            graph_data = json.loads(response) if isinstance(response, str) else response
            graph = ActionGraph(**graph_data)
            logger.info(f"Generated ActionGraph with {len(graph.nodes)} nodes.")
            return graph
            
        except Exception as e:
            logger.error(f"Planner failed to generate graph: {e}")
            return None

    async def execute_plan(self, graph: ActionGraph):
        """
        Executes the acyclic graph. Nodes with no dependencies are executed first.
        """
        logger.info(f"Executing ActionGraph for goal: {graph.goal}")
        
        completed = set()
        results = {}
        
        while len(completed) < len(graph.nodes):
            progress_made = False
            
            for node in graph.nodes:
                if node.id in completed:
                    continue
                    
                # Check if all dependencies are met
                if all(dep in completed for dep in node.dependencies):
                    logger.info(f"Executing step {node.id}: {node.tool_name}")
                    
                    try:
                        if self.tool_manager and hasattr(self.tool_manager, "execute"):
                            res = await self.tool_manager.execute(node.tool_name, node.arguments)
                        else:
                            res = await tool_registry.execute_in_sandbox(node.tool_name, node.arguments)
                        results[node.id] = res
                        logger.info(f"Step {node.id} complete. Verification: {node.verification_step}")
                        completed.add(node.id)
                        progress_made = True
                    except Exception as e:
                        logger.error(f"Execution failed at step {node.id}: {e}")
                        return
                        
            if not progress_made:
                logger.error("Deadlock detected in ActionGraph dependencies!")
                break
                
        logger.info(f"ActionGraph execution finished. Results: {len(results)}")
