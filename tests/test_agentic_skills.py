import unittest
import os
import sys
import asyncio

sys.path.insert(0, os.path.abspath("."))

from auhip.skills.organizer import (
    patch_file,
    view_directory_tree,
    search_codebase,
    run_powershell_guarded,
    summarize_notebook,
    generate_audio_overview,
)


class TestAgenticSkills(unittest.IsolatedAsyncioTestCase):

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
        test_file = "scratch/test_patch_sample.txt"
        os.makedirs("scratch", exist_ok=True)
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("Hello Alpha World")

        # Patch Alpha -> Beta
        res = await patch_file(test_file, "Alpha", "Beta")
        self.assertIn("Successfully patched", res)

        with open(test_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertEqual(content, "Hello Beta World")

        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)

    async def test_run_powershell_guarded(self):
        # Safe command
        out = await run_powershell_guarded("Get-Location")
        self.assertIn("PowerShell Output", out)

        # Blocked dangerous command
        blocked = await run_powershell_guarded("rmdir /s /q c:")
        self.assertIn("Security Restriction", blocked)

    async def test_notebooklm_skills(self):
        summary = await summarize_notebook("project")
        self.assertIsNotNone(summary)
        self.assertIn("Notebook Summary", summary)

        overview = await generate_audio_overview("AUHIP Architecture")
        self.assertIsNotNone(overview)
        self.assertIn("Alex", overview)
        self.assertIn("Taylor", overview)


if __name__ == "__main__":
    unittest.main()
