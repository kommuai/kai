"""Studio skill on/off toggles — workspace.yaml profile_overrides.enabled."""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "studio" / "backend"))

from kai_capabilities import get_capabilities  # noqa: E402
from skill_toggle import set_profile_skill_enabled  # noqa: E402


class StudioSkillToggleTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()
        fixture = ROOT / "tests" / "fixtures" / "minimal_workspace"
        shutil.copytree(fixture, Path(self._tmp) / "ws", dirs_exist_ok=True)
        self.home = Path(self._tmp) / "ws"

    def tearDown(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_disable_and_enable_profile_skill(self) -> None:
        set_profile_skill_enabled(self.home, "search_web", False)
        caps = get_capabilities(self.home)
        web = next(s for s in caps["skills"] if s["id"] == "search_web")
        self.assertFalse(web["enabled"])

        set_profile_skill_enabled(self.home, "search_web", True)
        caps2 = get_capabilities(self.home)
        web2 = next(s for s in caps2["skills"] if s["id"] == "search_web")
        self.assertTrue(web2["enabled"])

    def test_disabled_skill_excluded_from_runtime_config(self) -> None:
        import os

        os.environ["KAI_HOME"] = str(self.home)
        from kai.settings import reload_settings
        from kai.workspace.tools_config import reload_tools_config

        reload_settings()
        reload_tools_config()
        set_profile_skill_enabled(self.home, "search_faq", False)
        reload_tools_config()
        ids = {e.id for e in reload_tools_config().enabled_entries()}
        self.assertNotIn("search_faq", ids)
        self.assertIn("search_session_memory", ids)


if __name__ == "__main__":
    unittest.main()
