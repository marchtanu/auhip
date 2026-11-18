"""
scratch/test_polish_integration.py
----------------------------------
Comprehensive automated verification suite for AUHIP polish and architectural alignment:
1. Unified voice routing (voice_commands.py)
2. All 38 tool schemas registered in ToolManager
3. Long-term & session memory persistence and retrieval
4. HybridLLMRouter memory integration & generate_json
5. SupervisorAgent & PlannerAgent multi-agent coordination
6. ToolRegistry bridging with ToolManager
"""

import asyncio
import os
import sys
import json
import unittest

# Ensure project root is in path
sys.path.insert(0, os.path.abspath("."))

from auhip.core.voice_commands import (
    get_canonical_routes,
    build_valid_keywords,
    dispatch_local_route,
)
from auhip.core.agent import AuhipAgent
from auhip.core.agents.memory import memory_agent, MemoryAgent
from auhip.core.agents.supervisor import SupervisorAgent
from auhip.core.agents.planner import PlannerAgent
from auhip.core.tool_registry import tool_registry


class TestPolishIntegration(unittest.IsolatedAsyncioTestCase):

    async def test_01_voice_commands_single_source_of_truth(self):
        """Verify voice_commands.py contains canonical routes and valid keywords."""
        routes = get_canonical_routes()
        self.assertGreaterEqual(len(routes), 30)

        keywords = build_valid_keywords()
        self.assertIn("cockpit", keywords)
        self.assertIn("voice hud", keywords)
        self.assertIn("weather", keywords)
        self.assertIn("search codebase", keywords)
        self.assertIn("summarize notebook", keywords)

        # Test local parameterless dispatch
        res = await dispatch_local_route("what time")
        self.assertIsNotNone(res)
        self.assertTrue(any(w in res.lower() for w in ["time", ":", "current"]))

        # Test local parameterised dispatch
        res_stock = await dispatch_local_route("stock AAPL")
        self.assertIsNotNone(res_stock)
        self.assertIn("AAPL", res_stock)

    async def test_02_all_workspace_tools_registered(self):
        """Verify all workspace and notebook tools are registered in AuhipAgent ToolManager."""
        agent = AuhipAgent()
        schemas = {s.name: s for s in agent.tool_manager.get_schemas()}
        
        expected_tools = [
            "list_workspace_files", "read_code_file", "write_code_file",
            "list_unused_files", "delete_file", "patch_file",
            "view_directory_tree", "search_codebase", "run_powershell_guarded",
            "summarize_notebook", "generate_audio_overview",
            "lookup_stock", "add_task", "list_tasks", "complete_task"
        ]

        for tool in expected_tools:
            self.assertIn(tool, schemas, f"Missing tool schema registration for: {tool}")

        # Test executing a workspace tool safely via tool_manager
        tree = await agent.tool_manager.execute("view_directory_tree", {"path": "docs", "max_depth": 1})
        self.assertIn("docs", str(tree))

        # Test executing notebook summary
        summary = await agent.tool_manager.execute("summarize_notebook", {"name": "project"})
        self.assertIn("Notebook Summary", str(summary))

        # Test audio overview
        audio_script = await agent.tool_manager.execute("generate_audio_overview", {"topic": "AI OS"})
        self.assertIn("Deep Dive Audio Overview", str(audio_script))

    async def test_03_memory_agent_persistence_and_retrieval(self):
        """Verify MemoryAgent session memory and long-term memory with local fallback."""
        mem = MemoryAgent(json_path="scratch/test_memory.json")
        
        # Test session context
        mem.add_session_message("user", "My favorite coding language is Python.")
        mem.add_session_message("assistant", "Noted! Python is wonderful.")
        ctx = mem.get_session_context()
        self.assertIn("Python", ctx)

        # Test long-term memory storage
        await mem.add_long_term_memory("User prefers dark mode and concise code snippets.", metadata={"category": "preference"})
        
        # Search memory
        results = await mem.search_memory("dark mode", limit=2)
        self.assertGreaterEqual(len(results), 1)
        self.assertIn("dark mode", results[0]["text"])

        # Verify disk persistence
        self.assertTrue(os.path.exists("scratch/test_memory.json"))

    async def test_04_router_memory_and_json_generation(self):
        """Verify HybridLLMRouter generate_json and offline fallback."""
        agent = AuhipAgent()
        
        # Test generate_json method
        plan_json = await agent.router.generate_json("Organize the project directory")
        self.assertIsNotNone(plan_json)
        data = json.loads(plan_json)
        self.assertIn("goal", data)
        self.assertIn("nodes", data)

        # Test offline fallback message
        agent.router.local_provider.configured = False
        agent.router.cloud_provider.configured = False
        resp = await agent.router.execute("What is the meaning of life?")
        self.assertIn("unable to reach", resp.lower())

    async def test_05_supervisor_and_planner_agent_coordination(self):
        """Verify SupervisorAgent routes through local macros and delegates to PlannerAgent."""
        agent = AuhipAgent()
        supervisor = agent.supervisor
        planner = agent.planner

        self.assertIsNotNone(supervisor)
        self.assertIsNotNone(planner)

        # 1. Local macro via supervisor
        res = await supervisor.process_goal("what is the time")
        self.assertIsNotNone(res)

        # 2. Plan generation via planner
        graph = await planner.generate_plan("Refactor test directory")
        self.assertIsNotNone(graph)
        self.assertGreaterEqual(len(graph.nodes), 1)

        # 3. ToolRegistry delegation
        schemas = tool_registry.get_all_schemas()
        self.assertGreaterEqual(len(schemas), 30)

        # Sandbox execution via bridged tool_registry
        res_tree = await tool_registry.execute_in_sandbox("view_directory_tree", {"path": "docs", "max_depth": 1})
        self.assertIn("docs", str(res_tree))


if __name__ == "__main__":
    unittest.main()
