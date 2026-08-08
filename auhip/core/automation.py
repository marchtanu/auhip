import asyncio
import logging
from typing import Dict, List, Callable, Any
from dataclasses import dataclass
from auhip.core.event_bus import event_bus, EventPriority
from auhip.core.agents.planner import ActionGraph

logger = logging.getLogger(__name__)

@dataclass
class WorkflowTrigger:
    trigger_type: str # 'schedule', 'file_event', 'webhook', 'voice'
    condition: Callable[..., bool]
    action_goal: str

class WorkflowEngine:
    """
    Evaluates background triggers and dispatches automated workflows 
    to the Planner Agent without user intervention.
    """
    def __init__(self):
        self.triggers: List[WorkflowTrigger] = []
        
        # We hook into global events that might trigger a workflow
        event_bus.subscribe("FILE_CHANGED", self._evaluate_file_triggers)
        event_bus.subscribe("CRON_TICK", self._evaluate_schedule_triggers)
        logger.info("WorkflowEngine initialized.")

    def add_trigger(self, trigger: WorkflowTrigger):
        self.triggers.append(trigger)
        logger.info(f"Added workflow trigger for: {trigger.trigger_type}")

    async def _evaluate_file_triggers(self, data: dict):
        for trigger in self.triggers:
            if trigger.trigger_type == "file_event":
                try:
                    if trigger.condition(data):
                        logger.info(f"Trigger matched for goal: {trigger.action_goal}")
                        await event_bus.publish(
                            "DELEGATE_TO_PLANNER", 
                            data={"goal": trigger.action_goal},
                            priority=EventPriority.LOW
                        )
                except Exception as e:
                    logger.error(f"Error evaluating trigger: {e}")

    async def _evaluate_schedule_triggers(self, current_time: float):
        for trigger in self.triggers:
            if trigger.trigger_type == "schedule":
                try:
                    if trigger.condition(current_time):
                        logger.info(f"Schedule trigger matched for goal: {trigger.action_goal}")
                        await event_bus.publish(
                            "DELEGATE_TO_PLANNER", 
                            data={"goal": trigger.action_goal},
                            priority=EventPriority.LOW
                        )
                except Exception as e:
                    logger.error(f"Error evaluating trigger: {e}")

workflow_engine = WorkflowEngine()

# Example built-in workflow:
# Every time a file named 'invoice.pdf' is created, trigger parsing
workflow_engine.add_trigger(
    WorkflowTrigger(
        trigger_type="file_event",
        condition=lambda event: "invoice" in event.get("path", "").lower() and event.get("action") == "created",
        action_goal="Extract total amount and date from the new invoice PDF and append to expenses.csv"
    )
)
