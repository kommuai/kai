"""pre_router handover keywords and copy come from workspace.yaml only."""
from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from kai.content.channels import reload_channel_config
from kai.content.copy import reload_chat_copy
from kai.lib.session_state import init_db, reset_memory
from kai.services.container import kai_service


class PreRouterWorkspaceKeywordTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()
        fixture = Path(__file__).resolve().parent / "fixtures" / "minimal_workspace"
        self.home = Path(self._tmp) / "ws"
        shutil.copytree(fixture, self.home)
        self.uid = "pre_router_kw_test"

        import yaml

        data = yaml.safe_load((self.home / "workspace.yaml").read_text(encoding="utf-8"))
        data.setdefault("channels", {}).setdefault("handover", {})
        data["channels"]["handover"]["live_agent_keywords"] = ["HELP"]
        data["channels"]["handover"]["resume_keywords"] = ["GO"]
        data.setdefault("copy", {}).setdefault("handover", {})
        data["copy"]["handover"]["live_agent_en"] = "Custom live agent handover EN."
        data["copy"]["resume"] = {"en": "Custom resume EN.", "bm": "Custom resume BM."}
        (self.home / "workspace.yaml").write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")

        os.environ["KAI_HOME"] = str(self.home)
        from kai.settings import reload_settings
        from kai.workspace.manifest import reload_workspace_manifest

        reload_settings()
        reload_workspace_manifest()
        reload_chat_copy()
        reload_channel_config()
        init_db()
        reset_memory(self.uid)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_custom_live_agent_keyword_triggers_handover_copy(self) -> None:
        out = kai_service.pre_router({"content": "HELP", "phone_number": self.uid})
        self.assertIsNotNone(out)
        assert out is not None
        self.assertEqual(out.get("type"), "handover")
        self.assertIn("Custom live agent handover EN", out.get("message", ""))

    def test_legacy_la_does_not_handover_when_not_configured(self) -> None:
        out = kai_service.pre_router({"content": "LA", "phone_number": self.uid})
        self.assertIsNone(out)

    def test_custom_resume_keyword_when_frozen(self) -> None:
        from kai.lib.session_state import freeze

        freeze(self.uid, True)
        out = kai_service.pre_router({"content": "GO", "phone_number": self.uid})
        self.assertIsNotNone(out)
        assert out is not None
        self.assertEqual(out.get("type"), "reply")
        self.assertIn("Custom resume EN", out.get("message", ""))


if __name__ == "__main__":
    unittest.main()
