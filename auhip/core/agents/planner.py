import logging
import json
import asyncio
from dataclasses import asdict, is_dataclass
from typing import List, Dict, Any
from pydantic import BaseModel, Field

from auhip.core.event_bus import event_bus
from auhip.core.tool_registry import tool_registry
from auhip.core.llm.tool_selection import select_relevant_tools
from auhip.core.llm.types import ToolResult

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
    Validates plans before execution and reports step results. It does not provide rollback.
    """
    def __init__(self, llm_router, tool_manager=None):
        self.llm_router = llm_router
        self.tool_manager = tool_manager
        self._jobs: set[asyncio.Task] = set()
        event_bus.subscribe("DELEGATE_TO_PLANNER", self.handle_planning_request)
        event_bus.subscribe("CANCEL_ALL", self.cancel_plans)
        logger.info("PlannerAgent initialized.")

    def handle_planning_request(self, payload: dict) -> None:
        """Keep the event dispatcher available for approvals and cancellation."""
        if not isinstance(payload, dict) or not payload.get("goal"):
            return
        task = asyncio.create_task(self._run_planning_request(payload), name="planner_job")
        self._jobs.add(task)
        task.add_done_callback(self._on_job_done)

    def _on_job_done(self, task: asyncio.Task) -> None:
        self._jobs.discard(task)
        if not task.cancelled() and task.exception():
            logger.error("Planner job failed", exc_info=task.exception())

    def cancel_plans(self, data: dict | None = None) -> None:
        for task in list(self._jobs):
            task.cancel()

    async def close(self) -> None:
        event_bus.unsubscribe("DELEGATE_TO_PLANNER", self.handle_planning_request)
        event_bus.unsubscribe("CANCEL_ALL", self.cancel_plans)
        jobs = list(self._jobs)
        self.cancel_plans()
        await asyncio.gather(*jobs, return_exceptions=True)

    async def _run_planning_request(self, payload: dict) -> None:
        try:
            await self._plan_and_execute(payload)
        except asyncio.CancelledError:
            await event_bus.publish("AUHIP_RESPONSE", {
                "text": "Plan cancellation requested. Completed actions are not undone.",
                "type": "warning",
            })
            raise

    async def _plan_and_execute(self, payload: dict) -> None:
        goal = payload.get("goal")
        if not goal:
            return
            
        logger.info(f"PlannerAgent received goal: {goal}")
        
        # 1. Generate Plan
        graph = await self.generate_plan(goal, allow_cloud=bool(payload.get("allow_cloud", False)))

        if graph:
            # 2. Execute Plan
            await self.execute_plan(graph)
        else:
            await event_bus.publish("AUHIP_RESPONSE", {
                "text": "I couldn't create a valid plan for that request. No plan steps were run.",
                "type": "error",
            })
            
    async def generate_plan(self, goal: str, allow_cloud: bool = False) -> ActionGraph:
        """Uses the LLM to convert a goal into an ActionGraph."""
        if self.tool_manager:
            raw_schemas = self.tool_manager.get_schemas()
        else:
            raw_schemas = tool_registry.get_all_schemas()
        selected_schemas = select_relevant_tools(goal, raw_schemas)
        schemas = [asdict(s) if is_dataclass(s) else s.to_dict() if hasattr(s, "to_dict") else s
                   for s in selected_schemas]
        
        prompt = (
            f"Goal: {goal}\n"
            "Create a multi-step action plan using the available tools. "
            "Output MUST be valid JSON matching the ActionGraph schema: "
            "{'goal': '...', 'nodes': [{'id': 'step1', 'tool_name': '...', 'arguments': {}, 'dependencies': [], 'verification_step': '...'}]}"
        )
        
        try:
            # Enforce JSON mode via the router
            response = await self.llm_router.generate_json(prompt, schemas, allow_cloud=allow_cloud)
            if not response:
                raise ValueError("No planner response was produced; refusing to invent fallback steps.")
            
            # Parse the JSON into our Pydantic model
            graph_data = json.loads(response) if isinstance(response, str) else response
            graph = ActionGraph(**graph_data)
            self._validate_plan(graph, {schema["name"] for schema in schemas})
            logger.info(f"Generated ActionGraph with {len(graph.nodes)} nodes.")
            return graph
            
        except Exception as e:
            logger.error(f"Planner failed to generate graph: {e}")
            return None

    def _validate_plan(self, graph: ActionGraph, allowed_tool_names: set[str] | None = None) -> None:
        """Reject malformed plans before they can invoke any registered tool."""
        if not graph.nodes:
            raise ValueError("The generated plan has no steps.")

        node_ids = [node.id for node in graph.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("The generated plan contains duplicate step IDs.")

        known_ids = set(node_ids)
        exposed_tools = allowed_tool_names
        available_tools = set(self.tool_manager._tools) if self.tool_manager else {
            schema["name"] for schema in tool_registry.get_all_schemas()
        }
        for node in graph.nodes:
            if node.tool_name not in available_tools:
                raise ValueError(f"The plan references unknown tool '{node.tool_name}'.")
            if exposed_tools is not None and node.tool_name not in exposed_tools:
                raise ValueError(f"The plan references tool '{node.tool_name}' that was not exposed for this goal.")
            if self.tool_manager:
                schema = self.tool_manager._tools[node.tool_name][0]
                self.tool_manager.validate_arguments(schema, node.arguments)
            unknown_dependencies = set(node.dependencies) - known_ids
            if unknown_dependencies:
                raise ValueError(f"Step '{node.id}' has unknown dependencies: {sorted(unknown_dependencies)}.")
            if node.id in node.dependencies:
                raise ValueError(f"Step '{node.id}' cannot depend on itself.")

        completed = set()
        while len(completed) < len(graph.nodes):
            ready = {node.id for node in graph.nodes
                     if node.id not in completed and set(node.dependencies) <= completed}
            if not ready:
                raise ValueError("The generated plan contains a dependency cycle.")
            completed.update(ready)

    async def execute_plan(self, graph: ActionGraph):
        """
        Executes the acyclic graph. Nodes with no dependencies are executed first.
        """
        logger.info(f"Executing ActionGraph for goal: {graph.goal}")
        self._validate_plan(graph)
        
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
                        if self.tool_manager:
                            outcome = await self.tool_manager.execute_result(node.tool_name, node.arguments)
                        else:
                            outcome = ToolResult.from_output(
                                await tool_registry.execute_in_sandbox(node.tool_name, node.arguments)
                            )
                        if not outcome.succeeded:
                            raise RuntimeError(str(outcome.output))
                        res = outcome.output
                        results[node.id] = res
                        logger.info("Step %s completed with result: %s", node.id, str(res)[:500])
                        completed.add(node.id)
                        progress_made = True
                    except Exception as e:
                        logger.error(f"Execution failed at step {node.id}: {e}")
                        await event_bus.publish("AUHIP_RESPONSE", {
                            "text": f"Plan stopped at step '{node.id}' ({node.tool_name}): {e}",
                            "type": "error",
                        })
                        return
                        
            if not progress_made:
                logger.error("Deadlock detected in ActionGraph dependencies!")
                break
                
        summary = "\n".join(f"{step_id}: {str(result)[:300]}" for step_id, result in results.items())
        await event_bus.publish("AUHIP_RESPONSE", {
            "text": f"Plan finished: {len(results)} of {len(graph.nodes)} steps completed.\n{summary}",
            "type": "info" if len(results) == len(graph.nodes) else "error",
        })
        logger.info("ActionGraph execution finished. Results: %s/%s", len(results), len(graph.nodes))
