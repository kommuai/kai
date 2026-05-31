"""Phase 1-C: corpus_map.json emitted at compile time."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path


def _write_minimal_faq(path: Path, n_intents: int = 3) -> None:
    lines = ["# Support FAQ\n"]
    for i in range(n_intents):
        lines.append(f"\n## intent: faq_intent_{i}\n")
        lines.append(f"aliases:\n- question {i}\n- q{i}\n")
        lines.append(f"answer:\nAnswer number {i}.\n")
    path.write_text("".join(lines), encoding="utf-8")


class CorpusMapTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._home = Path(self._tmp) / "tenant_home"
        self._home.mkdir()
        knowledge_dir = self._home / "knowledge"
        knowledge_dir.mkdir()
        self._faq_path = knowledge_dir / "master_faq.md"
        compiled_dir = self._home / "compiled"
        compiled_dir.mkdir()
        self._compiled_dir = compiled_dir
        os.environ["KAI_HOME"] = str(self._home)

    def tearDown(self):
        os.environ.pop("KAI_HOME", None)
        from kai.settings import get_settings as _gs
        try:
            _gs.cache_clear()  # type: ignore[attr-defined]
        except Exception:
            pass

    def _compile(self) -> dict:
        from kai.settings import get_settings
        try:
            get_settings.cache_clear()  # type: ignore[attr-defined]
        except Exception:
            pass
        from kai.support_runtime.compiler import compile_canonical_knowledge
        return compile_canonical_knowledge()

    def test_corpus_map_written_after_compile(self):
        _write_minimal_faq(self._faq_path, n_intents=3)
        self._compile()
        map_path = self._compiled_dir / "corpus_map.json"
        self.assertTrue(map_path.is_file(), "corpus_map.json not created")

    def test_corpus_map_has_required_keys(self):
        _write_minimal_faq(self._faq_path, n_intents=2)
        self._compile()
        data = json.loads((self._compiled_dir / "corpus_map.json").read_text())
        for key in ("schema_version", "compiled_at", "source", "total_chunks", "intents"):
            self.assertIn(key, data, f"Missing key: {key}")

    def test_corpus_map_schema_version_is_1(self):
        _write_minimal_faq(self._faq_path, n_intents=1)
        self._compile()
        data = json.loads((self._compiled_dir / "corpus_map.json").read_text())
        self.assertEqual(data["schema_version"], 1)

    def test_corpus_map_intent_count_matches_faq(self):
        n = 4
        _write_minimal_faq(self._faq_path, n_intents=n)
        result = self._compile()
        self.assertEqual(result["intents"], n)
        data = json.loads((self._compiled_dir / "corpus_map.json").read_text())
        self.assertEqual(len(data["intents"]), n)

    def test_corpus_map_empty_faq_no_crash(self):
        self._faq_path.write_text("", encoding="utf-8")
        self._compile()
        data = json.loads((self._compiled_dir / "corpus_map.json").read_text())
        self.assertEqual(data["total_chunks"], 0)
        self.assertEqual(data["intents"], [])

    def test_corpus_map_compiled_at_is_date_string(self):
        _write_minimal_faq(self._faq_path, n_intents=1)
        self._compile()
        data = json.loads((self._compiled_dir / "corpus_map.json").read_text())
        import re
        self.assertRegex(data["compiled_at"], r"^\d{4}-\d{2}-\d{2}$")

    def test_system_prompt_includes_kb_summary(self):
        _write_minimal_faq(self._faq_path, n_intents=2)
        self._compile()
        from kai.support_runtime.agent_context import _corpus_map_summary
        summary = _corpus_map_summary()
        self.assertIn("chunks", summary.lower())
        self.assertGreater(len(summary), 0)

    def test_system_prompt_kb_summary_absent_when_no_map(self):
        # No compile run — no corpus_map.json
        from kai.support_runtime.agent_context import _corpus_map_summary
        summary = _corpus_map_summary()
        # Should return empty string, not crash
        self.assertIsInstance(summary, str)


if __name__ == "__main__":
    unittest.main()
