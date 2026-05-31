import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from shadou.settings.loader import load_settings
from shadou.support_runtime.compiler import compile_canonical_knowledge


class SopFaqPathAlignmentTests(unittest.TestCase):
    def test_compiler_and_resolve_use_same_master_faq(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td) / "agent_workspace"
            ws.mkdir(parents=True)
            faq = ws / "master_faq.md"
            faq.write_text(
                "## intent: demo\naliases:\n- hello\nanswer:\nHi\n",
                encoding="utf-8",
            )
            (ws / "compiled").mkdir(parents=True, exist_ok=True)
            (ws / "workspace.yaml").write_text(
                f'version: "2"\n'
                f"tenant:\n  id: test\n  display_name: Test\n"
                f"paths:\n  knowledge_primary: master_faq.md\n"
                f"  knowledge_compiled_dir: compiled\n"
                f"knowledge:\n  compile: kb_chunks.jsonl\n",
                encoding="utf-8",
            )
            env = {"AGENT_WORKSPACE": str(ws), "MASTER_FAQ_PATH": str(faq)}
            with patch.dict("os.environ", env, clear=False):
                from shadou.settings.loader import get_settings

                get_settings.cache_clear()
                s = load_settings()
                resolved = s.resolve_master_faq_path()
                self.assertEqual(resolved, faq.resolve())
                with patch("shadou.support_runtime.compiler.get_settings", return_value=s):
                    counts = compile_canonical_knowledge()
                self.assertGreater(counts.get("chunks", 0), 0)
                get_settings.cache_clear()


if __name__ == "__main__":
    unittest.main()
