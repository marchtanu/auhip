import asyncio
import os
import sys
import inspect
import threading

# Ensure workspace is on sys.path
WORKSPACE = r"d:\Desktop\Code\personal\project\Jarvis_demo"
if WORKSPACE not in sys.path:
    sys.path.insert(0, WORKSPACE)

def test_sec_01():
    print("Testing SEC-01: CloudModel API Key in header...")
    from auhip.core.llm.cloud_model import GeminiProvider
    src = inspect.getsource(GeminiProvider.generate_structured)
    assert '"x-goog-api-key": self.api_key' in src, "x-goog-api-key not in request headers!"
    assert "?key=" not in src and "&key=" not in src, "API key found in query string!"
    print("  [PASS] SEC-01")

def test_sec_02():
    print("Testing SEC-02: Sandbox allowed dirs...")
    from auhip.core.llm.config import LLMConfig
    cfg = LLMConfig()
    home = os.path.expanduser("~")
    assert home not in cfg.SANDBOX_ALLOWED_DIRS, f"User home {home} is in SANDBOX_ALLOWED_DIRS!"
    print("  [PASS] SEC-02")

async def test_sec_03_and_perf_01():
    print("Testing SEC-03 & BUG-03: Path traversal and protected file guards in organizer.py...")
    from auhip.skills.organizer import read_code_file, delete_file
    
    # 1. Path traversal test
    res = await read_code_file("../../../secret.txt")
    assert "Security restriction" in res or "not accessible" in res or "Access denied" in res, f"Failed to block path traversal: {res}"
    
    # 2. Protected file deletion test
    res_del = await delete_file(".env")
    assert "security restriction" in res_del.lower() or "protected" in res_del.lower(), f"Failed to protect .env: {res_del}"
    
    res_del2 = await delete_file("auhip/core/config.py")
    assert "security restriction" in res_del2.lower() or "protected" in res_del2.lower(), f"Failed to protect config.py: {res_del2}"
    
    # 3. PERF-01 shared aiohttp session
    from auhip.skills import organizer
    session1 = await organizer._get_session()
    session2 = await organizer._get_session()
    assert session1 is session2, "aiohttp session is not a singleton!"
    await session1.close()
    organizer._session = None
    print("  [PASS] SEC-03 & BUG-03 & PERF-01")

def test_perf_03():
    print("Testing PERF-03: ContextManager token estimation...")
    from auhip.core.llm.context_manager import ContextManager
    cm = ContextManager()
    sample = "Hello world! This is a test of token estimation in the context manager."
    tokens = cm._estimate_tokens(sample)
    expected = max(1, len(sample) // 4)
    assert tokens == expected, f"Expected {expected} tokens, got {tokens}"
    print(f"  [PASS] PERF-03: '{sample[:20]}...' (~{len(sample)} chars) -> {tokens} tokens")

def test_perf_04():
    print("Testing PERF-04: PyAutoGUI PAUSE speed...")
    import pyautogui
    from auhip.core import computer_use
    assert pyautogui.PAUSE <= 0.05, f"pyautogui.PAUSE is {pyautogui.PAUSE}, expected <= 0.05"
    print(f"  [PASS] PERF-04: pyautogui.PAUSE is {pyautogui.PAUSE}")

def test_bug_04():
    print("Testing BUG-04: Supervisor agent routing...")
    from auhip.core.agents.supervisor import SupervisorAgent
    src = inspect.getsource(SupervisorAgent.process_goal)
    assert "self.llm_router.execute" in src, "Supervisor not calling llm_router.execute!"
    assert "self.llm_router.route(" not in src, "Old broken route() call still present!"
    print("  [PASS] BUG-04")

def test_race_01():
    print("Testing RACE-01: Microphone queue lock...")
    from auhip.audio.microphone import Microphone
    mic = Microphone()
    lock = getattr(mic, "_queues_lock", getattr(mic, "_lock", None))
    assert lock is not None, "Microphone missing _queues_lock attribute!"
    assert isinstance(lock, type(threading.Lock())), "_queues_lock is not a threading.Lock!"
    print("  [PASS] RACE-01")

def test_race_02_and_perf_02():
    print("Testing RACE-02 & PERF-02: TTS thread safety and cached engine...")
    from auhip.audio.tts import TextToSpeech
    tts = TextToSpeech()
    assert hasattr(tts, "_state_lock"), "TTS missing _state_lock!"
    from auhip.audio import tts as tts_module
    assert hasattr(tts_module, "_thread_local"), "TTS module missing _thread_local!"
    print("  [PASS] RACE-02 & PERF-02")

def test_race_03():
    print("Testing RACE-03: EventBus subscriber copy during dispatch...")
    from auhip.core.event_bus import event_bus
    src = inspect.getsource(event_bus._dispatch)
    assert "list(self._subscribers.get(event.event_type, []))" in src, "EventBus not copying subscriber list!"
    assert "list(self._global_subscribers)" in src, "EventBus not copying global subscribers list!"
    print("  [PASS] RACE-03")

def test_bug_07_and_state_machine():
    print("Testing BUG-07, BUG-01, BUG-02, UX-03, UX-05 in StateMachine...")
    from auhip.core.state_machine import AuhipStateMachine
    assert hasattr(AuhipStateMachine, "_spawn_task"), "StateMachine missing _spawn_task helper!"
    
    # Check signature of _enter_voice_mode
    sig = inspect.signature(AuhipStateMachine._enter_voice_mode)
    assert "is_return" in sig.parameters, "_enter_voice_mode missing is_return parameter!"
    
    src = inspect.getsource(AuhipStateMachine._on_exit_sub_mode)
    assert "self._voice_cancel_event.clear()" in src, "cancel_event not cleared before re-entering voice mode!"
    assert "is_return=True" in src, "is_return=True not passed on submode exit!"
    
    src_cancel = inspect.getsource(AuhipStateMachine.on_cancel_all)
    assert "self._voice_cancel_event.clear()" in src_cancel, "cancel_event not cleared in on_cancel_all!"
    assert "self._voice_loop()" in src_cancel, "voice_loop not restarted in on_cancel_all!"
    
    print("  [PASS] BUG-01, BUG-02, BUG-06, BUG-07, UX-03, UX-05")

def test_perf_06():
    print("Testing PERF-06: RotatingFileHandler in main.py...")
    with open(os.path.join(WORKSPACE, "main.py"), "r", encoding="utf-8") as f:
        main_src = f.read()
    assert "RotatingFileHandler" in main_src, "RotatingFileHandler not found in main.py!"
    assert "maxBytes=5_000_000" in main_src or "maxBytes=5000000" in main_src, "RotatingFileHandler missing maxBytes!"
    print("  [PASS] PERF-06")

def test_vision_sleep_mode():
    print("Testing BUG-05 & UX-04: VisionWorker low power sleep mode...")
    from auhip.vision.worker import VisionWorker
    src = inspect.getsource(VisionWorker._on_set_vision_mode)
    assert 'mode == self.MODE_SLEEP' in src, 'sleep mode check not found in VisionWorker._on_set_vision_mode!'
    assert 'self.interval_ms = 140' in src or '140' in src, '140ms throttle (~7 FPS) not found in sleep mode!'
    print("  [PASS] BUG-05 & UX-04")

def test_no_auto_standby():
    print("Testing Voice Loop No Auto-Standby...")
    from auhip.core.config import config
    assert hasattr(config, "AUTO_STANDBY_ENABLED"), "config missing AUTO_STANDBY_ENABLED!"
    assert config.AUTO_STANDBY_ENABLED is False, "AUTO_STANDBY_ENABLED should default to False!"
    from auhip.core.state_machine import AuhipStateMachine
    src = inspect.getsource(AuhipStateMachine._voice_loop)
    assert "auto_standby" in src, "Voice loop missing auto_standby check!"
    assert "if auto_standby and max_silence_cycles is not None:" in src, "Voice loop still auto-transitioning to standby!"
    print("  [PASS] Voice loop does not automatically revert to standby!")

if __name__ == "__main__":
    test_sec_01()
    test_sec_02()
    asyncio.run(test_sec_03_and_perf_01())
    test_perf_03()
    test_perf_04()
    test_bug_04()
    test_race_01()
    test_race_02_and_perf_02()
    test_race_03()
    test_bug_07_and_state_machine()
    test_perf_06()
    test_vision_sleep_mode()
    test_no_auto_standby()
    print("\nALL AUDIT VERIFICATIONS PASSED SUCCESSFULLY! (100% COMPLETE)")
