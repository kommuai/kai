"""pre_router handover keywords and copy come from workspace.yaml only."""
from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from shadou.content.channels import reload_channel_config
from shadou.content.copy import reload_chat_copy
from shadou.lib.session_state import init_db, reset_memory
from shadou.services.container import shadou_service


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

        os.environ["SHADOU_HOME"] = str(self.home)
        from shadou.settings import reload_settings
        from shadou.workspace.manifest import reload_workspace_manifest

        reload_settings()
        reload_workspace_manifest()
        reload_chat_copy()
        reload_channel_config()
        init_db()
        reset_memory(self.uid)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_custom_live_agent_keyword_triggers_handover_copy(self) -> None:
        out = shadou_service.pre_router({"content": "HELP", "phone_number": self.uid})
        self.assertIsNotNone(out)
        assert out is not None
        self.assertEqual(out.get("type"), "handover")
        self.assertIn("Custom live agent handover EN", out.get("message", ""))

    def test_legacy_la_does_not_handover_when_not_configured(self) -> None:
        out = shadou_service.pre_router({"content": "LA", "phone_number": self.uid})
        self.assertIsNone(out)

    def test_custom_resume_keyword_when_frozen(self) -> None:
        from shadou.lib.session_state import freeze

        freeze(self.uid, True)
        out = shadou_service.pre_router({"content": "GO", "phone_number": self.uid})
        self.assertIsNotNone(out)
        assert out is not None
        self.assertEqual(out.get("type"), "reply")
        self.assertIn("Custom resume EN", out.get("message", ""))


if __name__ == "__main__":
    unittest.main()
