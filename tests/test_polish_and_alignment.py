import asyncio
import os
import sys
import inspect
import tempfile
import json

WORKSPACE = r"d:\Desktop\Code\personal\project\Jarvis_demo"
if WORKSPACE not in sys.path:
    sys.path.insert(0, WORKSPACE)

def test_qt_conf():
    print("Testing ARCH-03: qt.conf configuration...")
    conf_path = os.path.join(WORKSPACE, "qt.conf")
    assert os.path.exists(conf_path), "qt.conf does not exist in project root!"
    with open(conf_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "dpiawareness=0" in content, "dpiawareness=0 not found in qt.conf!"
    print("  [PASS] ARCH-03: qt.conf prevents Windows DPI awareness crash/warning.")

def test_voice_commands_single_source():
    print("Testing ARCH-01: voice_commands.py as single source of truth...")
    from auhip.core import voice_commands
    assert hasattr(voice_commands, "CANONICAL_ROUTES"), "CANONICAL_ROUTES missing!"
    assert hasattr(voice_commands, "get_canonical_routes"), "get_canonical_routes missing!"
    assert hasattr(voice_commands, "build_valid_keywords"), "build_valid_keywords missing!"
    assert hasattr(voice_commands, "dispatch_local_route"), "dispatch_local_route missing!"
    
    routes = voice_commands.get_canonical_routes()
    keywords = voice_commands.build_valid_keywords()
    
    print(f"  Canonical route handlers: {len(routes)}, Total valid keywords: {len(keywords)}")
    assert len(routes) >= 25, f"Expected >= 25 routes, got {len(routes)}"
    assert len(keywords) >= 50, f"Expected >= 50 keywords, got {len(keywords)}"

    # Test route matching via dispatch_local_route
    async def run_dispatch():
        res_cockpit = await voice_commands.dispatch_local_route("switch to cockpit")
        assert res_cockpit and "cockpit" in res_cockpit.lower(), f"Unexpected cockpit response: {res_cockpit}"

        res_tree = await voice_commands.dispatch_local_route("view directory tree")
        assert res_tree and ("Jarvis_demo" in res_tree or "Directory tree" in res_tree or "auhip" in res_tree), f"Unexpected directory tree response: {res_tree}"

        res_time = await voice_commands.dispatch_local_route("what time")
        assert res_time and ("AM" in res_time or "PM" in res_time or ":" in res_time), f"Unexpected time response: {res_time}"

        # Parameterised route
        res_weather = await voice_commands.dispatch_local_route("weather in Tokyo")
        assert res_weather and ("Tokyo" in res_weather or "weather" in res_weather.lower()), f"Unexpected weather response: {res_weather}"

    asyncio.run(run_dispatch())
    print("  [PASS] ARCH-01: Canonical routes and keyword derivations verified.")


async def test_tool_manager_registration_and_bridge():
    print("Testing ARCH-02: ToolManager registration (38 tools) and ToolRegistry bridge...")
    from auhip.core.llm.tool_manager import ToolManager
    from auhip.core.tool_registry import tool_registry
    from auhip.core.agent import AuhipAgent
    
    agent = AuhipAgent()
    tm = agent.tool_manager
    assert tm is not None, "AuhipAgent tool_manager is None!"
    
    registered_schemas = tm.get_schemas()
    schema_names = [s.name for s in registered_schemas]
    print(f"  Total registered tools in ToolManager: {len(registered_schemas)}")
    assert len(registered_schemas) >= 38, f"Expected at least 38 tools, found {len(registered_schemas)}: {schema_names}"
    
    # Check specific workspace and notebook tools
    expected_new_tools = [
        "patch_file", "view_directory_tree", "search_codebase",
        "run_powershell_guarded", "summarize_notebook", "generate_audio_overview"
    ]
    for t in expected_new_tools:
        assert t in schema_names, f"Expected tool '{t}' not found in registered tools!"

    # Check bridge to tool_registry
    bridge_schemas = tool_registry.get_all_schemas()
    bridge_names = [s["name"] for s in bridge_schemas]
    assert len(bridge_schemas) >= 38, f"ToolRegistry bridged tools count is {len(bridge_schemas)}, expected >= 38"
    assert "patch_file" in bridge_names, "patch_file not found in ToolRegistry bridge!"
    
    # Test sandboxed execution of view_directory_tree via ToolRegistry bridge
    res = await tool_registry.execute_in_sandbox("view_directory_tree", {"path": "docs", "max_depth": 1})
    assert "SYSTEM_AUDIT.md" in res or "docs" in res, f"view_directory_tree failed: {res}"
    print("  [PASS] ARCH-02: All 38 workspace/notebook tools registered and ToolRegistry bridge active.")

async def test_memory_agent_persistence_and_search():
    print("Testing ARCH-03: MemoryAgent persistence and fallback keyword search...")
    from auhip.core.agents.memory import MemoryAgent
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_store = os.path.join(tmpdir, "test_mem.json")
        mem = MemoryAgent(db_path=tmpdir, json_path=test_store)
        
        # Store memories
        await mem.add_long_term_memory("User prefers dark mode and minimal logging", {"category": "preference"}, importance=0.9)
        await mem.add_long_term_memory("Project workspace is Jarvis_demo with 38 agentic tools", {"category": "fact"}, importance=0.8)
        await mem.add_long_term_memory("Today we completed the system audit fixes", {"category": "conversation"}, importance=0.7)
        
        # Verify file persistence
        assert os.path.exists(test_store), "Memory JSON store was not created!"
        with open(test_store, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 3, f"Expected 3 records in JSON, got {len(data)}"
        
        # Test recall with keyword matching
        results = await mem.search_memory("UI dark mode preferences", limit=2)
        assert len(results) > 0, "No memories recalled!"
        assert any("dark mode" in r["text"] for r in results), f"Expected preference memory in results: {results}"
        
        print("  [PASS] ARCH-03: Memory persistence and retrieval operating reliably.")

async def test_supervisor_and_planner_execution():
    print("Testing ARCH-01: SupervisorAgent and PlannerAgent execution with ToolManager...")
    from auhip.core.agents.supervisor import SupervisorAgent
    from auhip.core.agents.planner import PlannerAgent
    from auhip.core.agent import AuhipAgent
    
    agent = AuhipAgent()
    planner = agent.planner
    supervisor = agent.supervisor
    
    assert supervisor.tool_manager is agent.tool_manager, "Supervisor tool_manager mismatch!"
    assert planner.tool_manager is agent.tool_manager, "Planner tool_manager mismatch!"

    # Test local fast route dispatch through supervisor
    res = await supervisor.process_goal("exit mode")
    assert "Exiting" in res or "Local route" in res or "Executing" in res or "mode" in res, f"Supervisor failed local route: {res}"

    print("  [PASS] ARCH-01: SupervisorAgent and PlannerAgent properly wired.")

def test_event_loop_deprecation_guards():
    print("Testing asyncio event loop deprecation fixes...")
    from auhip.core.llm import tool_manager
    from auhip.core import service_manager
    from auhip.audio import speech_recognition
    
    src_tm = inspect.getsource(tool_manager.ToolManager.execute)
    assert "asyncio.get_event_loop()" not in src_tm, "Deprecating get_event_loop() in ToolManager!"
    
    src_sm = inspect.getsource(service_manager.ManagedService.get)
    assert "asyncio.get_event_loop()" not in src_sm, "Deprecating get_event_loop() in ManagedService!"
    assert "asyncio.get_running_loop()" in src_sm, "Missing get_running_loop() in ManagedService!"

    src_sr = inspect.getsource(speech_recognition.SpeechRecognizer.listen_for_command)
    assert "asyncio.get_event_loop()" not in src_sr, "Deprecating get_event_loop() in SpeechRecognizer!"
    assert "asyncio.get_running_loop()" in src_sr, "Missing get_running_loop() in SpeechRecognizer!"
    
    print("  [PASS] Event loop deprecation calls eliminated.")

if __name__ == "__main__":
    test_qt_conf()
    test_voice_commands_single_source()
    asyncio.run(test_tool_manager_registration_and_bridge())
    asyncio.run(test_memory_agent_persistence_and_search())
    asyncio.run(test_supervisor_and_planner_execution())
    test_event_loop_deprecation_guards()
    print("\n========================================================")
    print("ALL POLISH AND ARCHITECTURAL INTEGRATION TESTS PASSED!")
    print("========================================================")
