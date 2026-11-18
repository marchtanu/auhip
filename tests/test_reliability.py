"""Behavioral checks with no real devices, cloud calls, or user-data mutations."""

import asyncio
import json
import os
import queue
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from auhip.core.event_bus import EventPriority, MultiQueueEventBus
from auhip.core.llm.tool_manager import ToolManager, resolve_tool_confirmation
from auhip.core.llm.types import ToolSchema, ToolStatus
from auhip.core.agents.planner import ActionGraph, ActionNode, PlannerAgent
from auhip.core.state_machine import AuhipStateMachine, State
from auhip.core.config import config
from auhip.audio.gemini_live_engine import GeminiLiveEngine
from auhip.core import voice_commands


class ReliabilityTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.bus = MultiQueueEventBus()
        self.patches = [patch(f"{module}.event_bus", self.bus) for module in (
            "auhip.core.llm.tool_manager", "auhip.core.agents.planner",
            "auhip.core.state_machine", "auhip.core.voice_commands", "auhip.audio.gemini_live_engine",
        )]
        self.patches.append(patch.dict(os.environ, {"AUHIP_ALLOW_UNSAFE_TOOLS": "false", "CLOUD_ENABLED": "false"}))
        for patcher in self.patches:
            patcher.start()
        self.bus.start()
        self.planners = []
        self.machines = []

    async def asyncTearDown(self) -> None:
        for machine in self.machines:
            await machine.stop()
        for planner in self.planners:
            await planner.close()
        await self.bus.stop()
        for patcher in reversed(self.patches):
            patcher.stop()

    def make_machine(self, execute=None, manager=None) -> AuhipStateMachine:
        async def listen(**kwargs):
            await asyncio.Event().wait()
        agent = SimpleNamespace(execute=execute or AsyncMock(return_value="done"),
                                is_valid_command=lambda text: True, tool_manager=manager or ToolManager())
        machine = AuhipStateMachine(SimpleNamespace(listen_for_command=listen), agent)
        self.machines.append(machine)
        return machine

    def make_planner(self, manager: ToolManager) -> PlannerAgent:
        planner = PlannerAgent(SimpleNamespace(), manager)
        self.planners.append(planner)
        return planner

    def capture(self, event_type: str) -> asyncio.Queue:
        events = asyncio.Queue()
        self.bus.subscribe(event_type, events.put_nowait)
        return events

    def approve_actions(self, approved: bool) -> None:
        self.bus.subscribe("TOOL_CONFIRMATION_REQUESTED", lambda data: resolve_tool_confirmation(data["request_id"], approved))

    async def test_delete_shortcut_requires_approval(self) -> None:
        manager = ToolManager()
        delete = AsyncMock(return_value="deleted")
        manager.register_tool(ToolSchema("delete_file", "delete", {"filename": {"type": "string"}}, ["filename"]), delete)
        self.approve_actions(False)
        result = await voice_commands.dispatch_local_route("delete file Sample.txt", manager)
        self.assertIn("not approved", result)
        delete.assert_not_awaited()

    async def test_approved_delete_keeps_filename_case(self) -> None:
        manager = ToolManager()
        delete = AsyncMock(return_value="deleted")
        manager.register_tool(ToolSchema("delete_file", "delete", {"filename": {"type": "string"}}, ["filename"]), delete)
        self.approve_actions(True)
        self.assertEqual(await voice_commands.dispatch_local_route("delete file Sample.txt", manager), "deleted")
        delete.assert_awaited_once_with(filename="Sample.txt")

    async def test_standalone_shortcut_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "sample.txt"
            target.write_text("keep", encoding="utf-8")
            with patch("auhip.core.tool_registry.tool_registry._tool_manager", None), patch(
                "auhip.skills.organizer._get_workspace_root", return_value=folder,
            ):
                result = await voice_commands.dispatch_local_route("delete file sample.txt")
            self.assertIn("not approved", result)
            self.assertEqual(target.read_text(encoding="utf-8"), "keep")

    async def test_approved_delete_reaches_real_file_boundary(self) -> None:
        from auhip.skills.organizer import delete_file
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "sample.txt"
            target.write_text("temporary fixture", encoding="utf-8")
            manager = ToolManager()
            manager.register_tool(ToolSchema("delete_file", "delete", {"filename": {"type": "string"}}), delete_file)
            self.approve_actions(True)
            with patch("auhip.skills.organizer._get_workspace_root", return_value=folder):
                result = await manager.execute_result("delete_file", {"filename": "sample.txt"})
            self.assertTrue(result.succeeded)
            self.assertFalse(target.exists())

    async def test_timer_is_not_time_and_accepts_full_duration(self) -> None:
        manager = ToolManager()
        timer = AsyncMock(return_value="timer started")
        clock = AsyncMock(return_value="clock")
        manager.register_tool(ToolSchema("set_timer", "timer", {"duration_str": {"type": "string"}}), timer)
        manager.register_tool(ToolSchema("tell_time", "clock"), clock)
        self.assertEqual(await voice_commands.dispatch_local_route("set a timer for 1 hour 30 minutes", manager), "timer started")
        timer.assert_awaited_once_with(duration_str="1 hour 30 minutes")
        clock.assert_not_awaited()
        self.assertEqual(await voice_commands.dispatch_local_route("what time is it?", manager), "clock")

    async def test_unrelated_language_does_not_trigger_shortcuts(self) -> None:
        manager = ToolManager()
        self.assertIsNone(await voice_commands.dispatch_local_route("update my saved memory", manager))
        self.assertIsNone(await voice_commands.dispatch_local_route("remember that I prefer time estimates", manager))
        self.assertIsNone(await voice_commands.dispatch_local_route("do not mute the volume", manager))

    async def test_explain_is_not_mistaken_for_a_plan(self) -> None:
        from auhip.core.agent import AuhipAgent
        agent = SimpleNamespace(
            _local_route=AsyncMock(return_value=None),
            supervisor=SimpleNamespace(process_goal=AsyncMock(return_value="plan")),
            router=SimpleNamespace(execute=AsyncMock(return_value="explanation")),
        )
        self.assertEqual(await AuhipAgent.execute(agent, "Explain Python loops"), "explanation")
        agent.supervisor.process_goal.assert_not_awaited()

    async def test_explicit_plan_request_still_delegates(self) -> None:
        from auhip.core.agent import AuhipAgent
        agent = SimpleNamespace(
            _local_route=AsyncMock(return_value=None),
            supervisor=SimpleNamespace(process_goal=AsyncMock(return_value="plan")),
            router=SimpleNamespace(execute=AsyncMock(return_value="explanation")),
        )
        self.assertEqual(await AuhipAgent.execute(agent, "Plan my workflow"), "plan")
        agent.supervisor.process_goal.assert_awaited_once_with("Plan my workflow")

    async def test_typed_and_ipc_commands_execute(self) -> None:
        machine = self.make_machine()
        await machine.start()
        results = self.capture("COMMAND_EXECUTED")
        for event_type, payload in (("PROCESS_COMMAND", {"command": "typed"}), ("PROCESS_GOAL", {"text": "ipc"})):
            await self.bus.publish(event_type, payload)
            result = await asyncio.wait_for(results.get(), 1)
            self.assertEqual(result["command"], next(iter(payload.values())))
            await asyncio.sleep(0)
        self.assertEqual(machine.agent.execute.await_count, 2)
        self.assertEqual(machine.state, State.STANDBY)

    async def test_voice_override_starts_listening(self) -> None:
        machine = self.make_machine()
        await machine.start()
        with patch.object(config, "VOICE_MODE_ENGINE", "classic"):
            await self.bus.publish("ENTER_VOICE_MODE", {})
            await asyncio.wait_for(self.bus._queue.join(), 1)
            await asyncio.sleep(0)
            self.assertEqual(machine.state, State.VOICE_MODE)
            self.assertIsNotNone(machine._voice_task)
            self.assertFalse(machine._voice_task.done())

    async def test_cancellation_stops_command_without_late_success(self) -> None:
        entered = asyncio.Event()
        finished = []
        async def action(text):
            entered.set()
            await asyncio.Event().wait()
            finished.append(text)
        machine = self.make_machine(action)
        await machine.start()
        results = self.capture("COMMAND_EXECUTED")
        await self.bus.publish("PROCESS_COMMAND", {"command": "work"})
        await asyncio.wait_for(entered.wait(), 1)
        await self.bus.publish("CANCEL_ALL", {}, priority=EventPriority.CRITICAL)
        await asyncio.wait_for(self.bus._queue.join(), 1)
        await asyncio.gather(machine._submitted_command_task, return_exceptions=True)
        self.assertEqual(finished, [])
        self.assertTrue(results.empty())
        self.assertEqual(machine.state, State.STANDBY)

    async def test_typed_command_resumes_voice_listener(self) -> None:
        machine = self.make_machine()
        await machine.start()
        with patch.object(config, "VOICE_MODE_ENGINE", "classic"):
            await machine._enter_voice_mode()
            old_event = machine._voice_cancel_event
            old_task = machine._voice_task
            machine._on_process_command({"command": "typed"})
            await machine._submitted_command_task
            self.assertTrue(old_event.is_set())
            self.assertTrue(old_task.done())
            self.assertIsNot(old_event, machine._voice_cancel_event)
            self.assertFalse(machine._voice_task.done())

    async def test_shutdown_does_not_restart_voice_after_cancelling_typed_work(self) -> None:
        entered = asyncio.Event()
        async def execute(text: str) -> str:
            entered.set()
            await asyncio.Event().wait()
        machine = self.make_machine(execute)
        with patch.object(config, "VOICE_MODE_ENGINE", "classic"):
            await machine._enter_voice_mode()
            machine._on_process_command({"command": "work"})
            await asyncio.wait_for(entered.wait(), 1)
            await machine.stop()
            self.assertTrue(machine._voice_task.done())
            self.assertTrue(machine._submitted_command_task.done())
            self.assertFalse(any(not task.done() for task in machine._active_tasks))

    async def test_sleep_cancels_typed_work_without_late_success(self) -> None:
        entered = asyncio.Event()
        async def execute(text: str) -> str:
            entered.set()
            await asyncio.Event().wait()
        machine = self.make_machine(execute)
        results = self.capture("COMMAND_EXECUTED")
        with patch.object(config, "VOICE_MODE_ENGINE", "classic"):
            await machine._enter_voice_mode()
            machine._on_process_command({"command": "work"})
            await asyncio.wait_for(entered.wait(), 1)
            await machine._on_enter_sleep_mode({})
            await machine._submitted_command_task
            self.assertEqual(machine.state, State.SLEEP)
            self.assertTrue(results.empty())

    async def test_reentering_voice_signals_previous_recognizer(self) -> None:
        machine = self.make_machine()
        with patch.object(config, "VOICE_MODE_ENGINE", "classic"):
            await machine._enter_voice_mode()
            previous_cancel_event = machine._voice_cancel_event
            previous_task = machine._voice_task
            await machine._enter_voice_mode(is_return=True)
            self.assertTrue(previous_cancel_event.is_set())
            self.assertTrue(previous_task.done())
            self.assertFalse(machine._voice_cancel_event.is_set())

    async def test_plan_approval_is_delivered_without_blocking_bus(self) -> None:
        manager = ToolManager()
        handler = AsyncMock(return_value="done")
        manager.register_tool(ToolSchema("reviewed_action", "test", requires_confirmation=True), handler)
        planner = self.make_planner(manager)
        planner.generate_plan = AsyncMock(return_value=ActionGraph(goal="test", nodes=[ActionNode(id="one", tool_name="reviewed_action", arguments={})]))
        self.approve_actions(True)
        responses = self.capture("AUHIP_RESPONSE")
        await self.bus.publish("DELEGATE_TO_PLANNER", {"goal": "test"})
        response = await asyncio.wait_for(responses.get(), 1)
        self.assertIn("1 of 1", response["text"])
        handler.assert_awaited_once()

    async def test_denied_plan_does_not_run_dependants(self) -> None:
        manager = ToolManager()
        first, dependent = AsyncMock(return_value="one"), AsyncMock(return_value="two")
        manager.register_tool(ToolSchema("first", "test", requires_confirmation=True), first)
        manager.register_tool(ToolSchema("dependent", "test"), dependent)
        self.approve_actions(False)
        planner = self.make_planner(manager)
        responses = self.capture("AUHIP_RESPONSE")
        await planner.execute_plan(ActionGraph(goal="test", nodes=[
            ActionNode(id="one", tool_name="first", arguments={}),
            ActionNode(id="two", tool_name="dependent", arguments={}, dependencies=["one"]),
        ]))
        response = await asyncio.wait_for(responses.get(), 1)
        self.assertIn("Plan stopped", response["text"])
        first.assert_not_awaited()
        dependent.assert_not_awaited()

    async def test_planner_can_be_cancelled_while_running(self) -> None:
        manager = ToolManager()
        entered = asyncio.Event()
        async def blocked():
            entered.set()
            await asyncio.Event().wait()
        manager.register_tool(ToolSchema("blocked", "test"), blocked)
        planner = self.make_planner(manager)
        planner.generate_plan = AsyncMock(return_value=ActionGraph(goal="test", nodes=[ActionNode(id="one", tool_name="blocked", arguments={})]))
        responses = self.capture("AUHIP_RESPONSE")
        await self.bus.publish("DELEGATE_TO_PLANNER", {"goal": "test"})
        await asyncio.wait_for(entered.wait(), 1)
        await self.bus.publish("CANCEL_ALL", {}, priority=EventPriority.CRITICAL)
        response = await asyncio.wait_for(responses.get(), 1)
        self.assertIn("cancellation requested", response["text"])
        await asyncio.gather(*planner._jobs, return_exceptions=True)

    async def test_planner_accepts_registered_dataclass_schemas(self) -> None:
        manager = ToolManager()
        manager.register_tool(ToolSchema("read_code_file", "read a file", {"filename": {"type": "string"}}, ["filename"]), AsyncMock())
        planner = self.make_planner(manager)
        planner.llm_router.generate_json = AsyncMock(return_value=json.dumps({
            "goal": "read file", "nodes": [{"id": "one", "tool_name": "read_code_file", "arguments": {"filename": "sample.py"}}],
        }))
        graph = await planner.generate_plan("read file sample.py")
        self.assertIsNotNone(graph)
        self.assertEqual(graph.nodes[0].tool_name, "read_code_file")

    async def test_cancelled_approval_closes_dialog_event(self) -> None:
        requests = self.capture("TOOL_CONFIRMATION_REQUESTED")
        closed = self.capture("TOOL_CONFIRMATION_CLOSED")
        manager = ToolManager()
        task = asyncio.create_task(manager.request_confirmation("action", {}))
        request = await asyncio.wait_for(requests.get(), 1)
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        event = await asyncio.wait_for(closed.get(), 1)
        self.assertEqual(event["request_id"], request["request_id"])

    async def test_tool_failures_have_explicit_status(self) -> None:
        manager = ToolManager()
        manager.register_tool(ToolSchema("test", "test"), AsyncMock(return_value="Error: unavailable"))
        result = await manager.execute_result("test", {})
        self.assertEqual(result.status, ToolStatus.FAILED)

    async def test_cancel_while_awaiting_approval_never_runs_action(self) -> None:
        requests = self.capture("TOOL_CONFIRMATION_REQUESTED")
        closed = self.capture("TOOL_CONFIRMATION_CLOSED")
        manager = ToolManager()
        action = AsyncMock(return_value="deleted")
        manager.register_tool(ToolSchema("delete_file", "delete", {"filename": {"type": "string"}}), action)
        async def execute(text: str) -> str:
            return await manager.execute("delete_file", {"filename": "sample.txt"})
        machine = self.make_machine(execute)
        await machine.start()
        await self.bus.publish("PROCESS_COMMAND", {"command": "delete sample"})
        request = await asyncio.wait_for(requests.get(), 1)
        await self.bus.publish("CANCEL_ALL", {}, priority=EventPriority.CRITICAL)
        event = await asyncio.wait_for(closed.get(), 1)
        self.assertEqual(event["request_id"], request["request_id"])
        resolve_tool_confirmation(request["request_id"], True)
        await asyncio.gather(machine._submitted_command_task, return_exceptions=True)
        action.assert_not_awaited()

    async def test_sleep_transition_does_not_cancel_itself(self) -> None:
        machine = self.make_machine()
        async def speak(text: str) -> None:
            await asyncio.sleep(0)
        machine.tts = SimpleNamespace(stop=lambda: None, speak=speak)
        machine.speech_recognizer.listen_for_command = AsyncMock(return_value="good night")
        machine.state = State.VOICE_MODE
        vision = self.capture("SET_VISION_MODE")
        machine._voice_task = machine._spawn_task(machine._voice_loop())
        await machine._voice_task
        self.assertEqual(machine.state, State.SLEEP)
        self.assertEqual((await asyncio.wait_for(vision.get(), 1))["mode"], "sleep")

    async def test_duplicate_submissions_do_not_overlap(self) -> None:
        entered, release = asyncio.Event(), asyncio.Event()
        async def execute(text: str) -> str:
            entered.set()
            await release.wait()
            return text
        machine = self.make_machine(AsyncMock(side_effect=execute))
        await machine.start()
        await self.bus.publish("PROCESS_COMMAND", {"command": "first"})
        await asyncio.wait_for(entered.wait(), 1)
        await self.bus.publish("PROCESS_COMMAND", {"command": "second"})
        await asyncio.wait_for(self.bus._queue.join(), 1)
        release.set()
        await machine._submitted_command_task
        machine.agent.execute.assert_awaited_once_with("first")

    async def test_plan_cycle_is_rejected_before_any_step(self) -> None:
        manager = ToolManager()
        action = AsyncMock(return_value="done")
        manager.register_tool(ToolSchema("action", "test"), action)
        planner = self.make_planner(manager)
        with self.assertRaises(ValueError):
            await planner.execute_plan(ActionGraph(goal="test", nodes=[
                ActionNode(id="one", tool_name="action", arguments={}, dependencies=["two"]),
                ActionNode(id="two", tool_name="action", arguments={}, dependencies=["one"]),
            ]))
        action.assert_not_awaited()

    async def test_cloud_disabled_never_constructs_live_engine(self) -> None:
        machine = self.make_machine()
        with patch.object(config, "VOICE_MODE_ENGINE", "gemini_live"), patch(
            "auhip.audio.gemini_live_engine.GeminiLiveEngine",
        ) as engine:
            await machine._enter_voice_mode()
            await asyncio.sleep(0)
            engine.assert_not_called()
            self.assertEqual(machine.state, State.VOICE_MODE)

    async def test_live_consent_cannot_be_bypassed_by_unsafe_tools_setting(self) -> None:
        machine = self.make_machine()
        with patch.dict(os.environ, {"CLOUD_ENABLED": "true", "AUHIP_ALLOW_UNSAFE_TOOLS": "true"}), patch.object(
            config, "VOICE_MODE_ENGINE", "gemini_live",
        ), patch("auhip.audio.gemini_live_engine.GeminiLiveEngine") as engine:
            await machine._enter_voice_mode()
            await asyncio.sleep(0)
            engine.assert_not_called()

    async def test_live_constructor_enforces_cloud_and_consent(self) -> None:
        with patch("auhip.audio.gemini_live_engine.genai.Client") as client:
            with self.assertRaises(PermissionError):
                GeminiLiveEngine(session_approved=True)
            with patch.dict(os.environ, {"CLOUD_ENABLED": "true"}):
                with self.assertRaises(PermissionError):
                    GeminiLiveEngine()
            client.assert_not_called()

    async def test_live_session_starts_after_explicit_approval(self) -> None:
        machine = self.make_machine()
        self.approve_actions(True)
        entered = asyncio.Event()
        async def run(**kwargs) -> None:
            entered.set()
            await asyncio.Event().wait()
        engine = SimpleNamespace(run=AsyncMock(side_effect=run), stop=MagicMock())
        with patch.dict(os.environ, {"CLOUD_ENABLED": "true"}), patch.object(
            config, "VOICE_MODE_ENGINE", "gemini_live",
        ), patch("auhip.audio.gemini_live_engine.GeminiLiveEngine", return_value=engine) as constructor:
            await machine._enter_voice_mode()
            await asyncio.wait_for(entered.wait(), 1)
            self.assertTrue(constructor.call_args.kwargs["session_approved"])
            machine._stop_voice_loop()
            await asyncio.gather(machine._voice_task, return_exceptions=True)

    def make_live_engine(self):
        client = MagicMock()
        client.aio.aclose = AsyncMock()
        with patch.dict(os.environ, {"CLOUD_ENABLED": "true", "GOOGLE_API_KEY": "fixture"}), patch(
            "auhip.audio.gemini_live_engine.genai.Client", return_value=client,
        ):
            engine = GeminiLiveEngine(mic=MagicMock(), session_approved=True)
        return engine, client

    async def test_live_receives_successive_model_turns(self) -> None:
        engine, _ = self.make_live_engine()
        engine.is_running = True
        turns = []
        two_turns = asyncio.Event()
        class Session:
            async def receive(self):
                turns.append(len(turns) + 1)
                if len(turns) > 2:
                    two_turns.set()
                    await asyncio.Event().wait()
                yield SimpleNamespace(server_content=SimpleNamespace(
                    interrupted=False, input_transcription=None, model_turn=None,
                    output_transcription=SimpleNamespace(text=f"turn {len(turns)}"), turn_complete=True,
                ))
        responses = self.capture("AUHIP_RESPONSE")
        task = asyncio.create_task(engine._receive_gemini_stream(Session()))
        try:
            await asyncio.wait_for(two_turns.wait(), 1)
            first = await asyncio.wait_for(responses.get(), 1)
            second = await asyncio.wait_for(responses.get(), 1)
            self.assertEqual([first["text"], second["text"]], ["turn 1", "turn 2"])
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def test_live_receive_failure_stops_sending_and_cleans_hardware(self) -> None:
        engine, client = self.make_live_engine()
        engine.mic.subscribe.return_value = queue.Queue()
        session = MagicMock()
        async def receive():
            raise ConnectionError("fixture disconnect")
            yield
        session.receive = receive
        session.send_client_content = AsyncMock()
        connection = client.aio.live.connect.return_value
        connection.__aenter__ = AsyncMock(return_value=session)
        connection.__aexit__ = AsyncMock(return_value=False)
        stream = MagicMock()
        with patch.dict(os.environ, {"CLOUD_ENABLED": "true"}), patch(
            "auhip.audio.gemini_live_engine.sd.OutputStream", return_value=stream,
        ):
            with self.assertRaises(ConnectionError):
                await engine.run()
        self.assertFalse(engine.is_running)
        self.assertTrue(engine._audio_in_task.done())
        engine.mic.unsubscribe.assert_called_once()
        stream.close.assert_called_once()
        client.aio.aclose.assert_awaited_once()

    async def test_live_output_startup_failure_releases_resources(self) -> None:
        engine, client = self.make_live_engine()
        stream = MagicMock()
        stream.start.side_effect = RuntimeError("fixture device unavailable")
        with patch.dict(os.environ, {"CLOUD_ENABLED": "true"}), patch(
            "auhip.audio.gemini_live_engine.sd.OutputStream", return_value=stream,
        ):
            with self.assertRaises(RuntimeError):
                await engine.run()
        self.assertFalse(engine.is_running)
        engine.mic.unsubscribe.assert_called_once()
        stream.close.assert_called_once()
        client.aio.aclose.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
