"""Phase 3-D: Corpus staleness detection."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from shadou.support_runtime.verifier import check_corpus_staleness


def _write_corpus_map(compiled_dir: Path, compiled_at: str) -> None:
    compiled_dir.mkdir(parents=True, exist_ok=True)
    (compiled_dir / "corpus_map.json").write_text(
        json.dumps({"schema_version": 1, "compiled_at": compiled_at, "total_chunks": 5, "intents": []}),
        encoding="utf-8",
    )


def _clear_caches():
    for fn in (
        "shadou.settings.get_settings",
        "shadou.workspace.runtime_settings.load_workspace_settings_yaml",
        "shadou.workspace.runtime_settings.get_runtime_settings",
        "shadou.workspace.manifest.load_workspace_data",
        "shadou.workspace.manifest._load_workspace_manifest_cached",
    ):
        try:
            mod_name, func_name = fn.rsplit(".", 1)
            import importlib
            mod = importlib.import_module(mod_name)
            getattr(mod, func_name).cache_clear()
        except Exception:
            pass


class CheckCorpusStalenessTests(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp())
        self._home = self._tmp / "tenant"
        self._home.mkdir()
        self._compiled = self._home / "compiled"
        self._compiled.mkdir()
        # Minimal workspace.yaml
        (self._home / "workspace.yaml").write_text(
            "version: '2'\ntenant:\n  id: test\n  display_name: Test\n  default_lang: en\n  timezone: UTC\n"
            "paths:\n  knowledge_compiled_dir: compiled\n"
            "eval:\n  max_corpus_age_days: 30\n",
            encoding="utf-8",
        )
        os.environ["SHADOU_HOME"] = str(self._home)
        _clear_caches()

    def tearDown(self):
        os.environ.pop("SHADOU_HOME", None)
        _clear_caches()

    def test_fresh_corpus_not_stale(self):
        today = date.today().isoformat()
        _write_corpus_map(self._compiled, today)
        self.assertFalse(check_corpus_staleness())

    def test_old_corpus_is_stale(self):
        old = (date.today() - timedelta(days=40)).isoformat()
        _write_corpus_map(self._compiled, old)
        self.assertTrue(check_corpus_staleness())

    def test_exactly_at_boundary_not_stale(self):
        # 30 days old with max 30 — NOT stale (age == limit, not >)
        boundary = (date.today() - timedelta(days=30)).isoformat()
        _write_corpus_map(self._compiled, boundary)
        self.assertFalse(check_corpus_staleness())

    def test_missing_corpus_map_not_stale(self):
        # No file — should return False, not crash
        self.assertFalse(check_corpus_staleness())

    def test_missing_compiled_at_not_stale(self):
        (self._compiled / "corpus_map.json").write_text(
            json.dumps({"schema_version": 1, "total_chunks": 0, "intents": []}),
            encoding="utf-8",
        )
        self.assertFalse(check_corpus_staleness())


class VerifierStalenessIntegrationTests(unittest.TestCase):
    """verify_result stamps stale_evidence on result metadata."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp())
        self._home = self._tmp / "tenant"
        self._home.mkdir()
        self._compiled = self._home / "compiled"
        self._compiled.mkdir()
        (self._home / "workspace.yaml").write_text(
            "version: '2'\ntenant:\n  id: test\n  display_name: Test\n  default_lang: en\n  timezone: UTC\n"
            "paths:\n  knowledge_compiled_dir: compiled\n"
            "eval:\n  max_corpus_age_days: 30\n  verifier_on_fail: flag\n",
            encoding="utf-8",
        )
        os.environ["SHADOU_HOME"] = str(self._home)
        _clear_caches()

    def tearDown(self):
        os.environ.pop("SHADOU_HOME", None)
        _clear_caches()

    def _run_verify(self, compiled_at: str):
        from shadou.support_runtime.models import EvidenceItem, RuntimeResult
        from shadou.support_runtime.verifier import verify_result
        _write_corpus_map(self._compiled, compiled_at)
        _clear_caches()
        ev = EvidenceItem(tool="search_faq", source_id="faq:x", snippet="some text", score=0.9)
        result = RuntimeResult(decision="direct_answer", answer="ok", confidence=0.85, evidence_ledger=[ev])
        return verify_result(result)

    def test_stale_corpus_sets_metadata_flag(self):
        old = (date.today() - timedelta(days=40)).isoformat()
        out = self._run_verify(old)
        self.assertTrue(out.metadata.get("stale_evidence"))

    def test_fresh_corpus_no_stale_flag(self):
        today = date.today().isoformat()
        out = self._run_verify(today)
        self.assertFalse(out.metadata.get("stale_evidence"))


class EvalRunStaleCitationRateTests(unittest.TestCase):
    def test_stale_citation_rate_in_results(self):
        from shadou.tools.eval_run import run_eval
        items = [{"question": "hi", "expected_decision": "direct_answer", "tags": []}]
        results = run_eval(items, open_book=True)
        self.assertIn("stale_citation_rate", results)

    def test_stale_citation_rate_is_float(self):
        from shadou.tools.eval_run import run_eval
        items = [{"question": "hello", "expected_decision": "direct_answer", "tags": []}]
        results = run_eval(items, open_book=True)
        self.assertIsInstance(results["stale_citation_rate"], float)

    def test_item_results_have_stale_evidence_field(self):
        from shadou.tools.eval_run import run_eval
        items = [{"question": "what is this?", "expected_decision": "direct_answer", "tags": []}]
        results = run_eval(items, open_book=True)
        for ir in results["items"]:
            self.assertIn("stale_evidence", ir)


if __name__ == "__main__":
    unittest.main()
