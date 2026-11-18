"""Run the device-free release checks using only the standard unittest runner."""

import asyncio
import importlib
import inspect
import os
from pathlib import Path
import sys
import unittest


def main() -> int:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["CLOUD_ENABLED"] = "false"
    os.environ["AUHIP_ALLOW_UNSAFE_TOOLS"] = "false"
    repository = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repository))
    sys.path.insert(0, str(repository / "tests"))
    suite = unittest.TestSuite()
    for name in ("test_reliability", "test_agentic_skills", "test_ambient_ui", "test_cockpit_view", "test_gui_tts"):
        suite.addTests(unittest.defaultTestLoader.loadTestsFromName(name))
    for name in ("test_audit_fixes", "test_polish_and_alignment"):
        module = importlib.import_module(name)
        for function_name, function in inspect.getmembers(module, inspect.isfunction):
            if function_name.startswith("test_"):
                if inspect.iscoroutinefunction(function):
                    def check(function=function) -> None:
                        asyncio.run(function())
                else:
                    check = function
                suite.addTest(unittest.FunctionTestCase(check, description=f"{name}.{function_name}"))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
