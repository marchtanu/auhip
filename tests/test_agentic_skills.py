import unittest
import os
import sys
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from auhip.core.llm.tool_manager import ToolManager
from auhip.core.llm.types import ToolSchema

from auhip.skills.organizer import (
    patch_file,
    view_directory_tree,
    search_codebase,
    run_powershell_guarded,
    summarize_notebook,
    generate_audio_overview,
)


class TestAgenticSkills(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / "main.py").write_text("class AuhipMainWindow: pass", encoding="utf-8")
        boundary = patch("auhip.skills.organizer._get_workspace_root", return_value=str(self.root))
        boundary.start()
        self.addCleanup(boundary.stop)
        self.manager = ToolManager()
        self.manager._request_confirmation = AsyncMock(return_value=True)
        self.manager.register_tool(ToolSchema("patch_file", "patch", {
            "path": {"type": "string"}, "target": {"type": "string"}, "replacement": {"type": "string"},
        }), patch_file)
        self.manager.register_tool(ToolSchema("run_powershell_guarded", "shell", {"command": {"type": "string"}}), run_powershell_guarded)

    async def test_view_directory_tree(self):
        tree = await view_directory_tree(".", max_depth=2)
        self.assertIsNotNone(tree)
        self.assertIn("📁", tree)
        self.assertIn("main.py", tree)

    async def test_search_codebase(self):
        res = await search_codebase("AuhipMainWindow")
        self.assertIsNotNone(res)
        self.assertIn("main.py", res)

    async def test_patch_file_and_revert(self):
        test_file = self.root / "sample.txt"
        test_file.write_text("Hello Alpha World", encoding="utf-8")
        result = await self.manager.execute("patch_file", {
            "path": "sample.txt", "target": "Alpha", "replacement": "Beta",
        })
        self.assertIn("Successfully patched", result)
        self.assertEqual(test_file.read_text(encoding="utf-8"), "Hello Beta World")

    async def test_run_powershell_guarded(self):
        process = AsyncMock()
        process.communicate.return_value = (b"fixture path", b"")
        with patch("auhip.skills.organizer.asyncio.create_subprocess_exec", return_value=process) as spawn:
            result = await self.manager.execute("run_powershell_guarded", {"command": "Get-Location"})
            self.assertIn("PowerShell Output", result)
            spawn.assert_awaited_once()
            blocked = await self.manager.execute("run_powershell_guarded", {"command": "rmdir /s /q c:"})
            self.assertIn("Security Restriction", blocked)
            self.assertEqual(spawn.await_count, 1)

    async def test_notebooklm_skills(self):
        previous_directory = os.getcwd()
        try:
            os.chdir(self.root)
            (self.root / "docs").mkdir()
            (self.root / "docs" / "sample.md").write_text("# Fixture\nA local project note.", encoding="utf-8")
            summary = await summarize_notebook("project")
        finally:
            os.chdir(previous_directory)
        self.assertIsNotNone(summary)
        self.assertIn("Notebook Summary", summary)

        overview = await generate_audio_overview("AUHIP Architecture")
        self.assertIsNotNone(overview)
        self.assertIn("Alex", overview)
        self.assertIn("Taylor", overview)


if __name__ == "__main__":
    unittest.main()
