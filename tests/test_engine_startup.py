import os
import unittest
from pathlib import Path
from unittest import mock

from shadou.engine.startup import should_compile_at_startup
from shadou.settings import get_settings


class StartupCompilePolicyTests(unittest.TestCase):
    def test_compile_off(self):
        with mock.patch.dict(os.environ, {"SHADOU_STARTUP_COMPILE": "0"}, clear=False):
            self.assertFalse(should_compile_at_startup())

    def test_compile_auto_when_chunks_missing(self):
        from shadou.workspace.manifest import load_workspace_manifest

        manifest = load_workspace_manifest()
        chunks = (
            get_settings().agent_workspace
            / manifest.paths.knowledge_compiled_dir
            / manifest.knowledge.compile_artifact
        )
        existed = chunks.is_file()
        try:
            if existed:
                chunks.unlink()
            with mock.patch.dict(os.environ, {"SHADOU_STARTUP_COMPILE": "auto"}, clear=False):
                self.assertTrue(should_compile_at_startup())
        finally:
            if existed and not chunks.is_file():
                chunks.touch()

    def test_compile_auto_when_chunks_present(self):
        from shadou.workspace.manifest import load_workspace_manifest

        manifest = load_workspace_manifest()
        chunks = (
            get_settings().agent_workspace
            / manifest.paths.knowledge_compiled_dir
            / manifest.knowledge.compile_artifact
        )
        if not chunks.is_file():
            self.skipTest("compiled kb not present")
        with mock.patch.dict(os.environ, {"SHADOU_STARTUP_COMPILE": "auto"}, clear=False):
            self.assertFalse(should_compile_at_startup())


if __name__ == "__main__":
    unittest.main()
