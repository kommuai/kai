"""Phase 3-C: Production turn metrics — TurnMetrics JSONL + metrics_report."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from shadou.support_runtime.models import EvidenceItem, RuntimeResult
from shadou.tools.metrics_report import compute_report, _load_rows


def _make_result(
    decision: str = "direct_answer",
    confidence: float = 0.85,
    verification_flagged: bool = False,
    tool_count: int = 0,
    stale: bool = False,
) -> RuntimeResult:
    meta: dict = {
        "agentic_route": {"steps": [{"step": i + 1} for i in range(tool_count)]},
        "verification": {"flagged": verification_flagged},
        "stale_evidence": stale,
    }
    return RuntimeResult(
        decision=decision,
        answer="ok",
        confidence=confidence,
        metadata=meta,
    )


class RecordTurnMetricsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp())
        self._metrics_file = self._tmp / "data" / "turn_metrics.jsonl"
        os.environ["SHADOU_HOME"] = str(self._tmp)
        # Write minimal workspace.yaml so metrics_path resolves
        ws = self._tmp / "workspace.yaml"
        ws.write_text(
            f"version: '2'\ntenant:\n  id: test\nlogging:\n  metrics_file: data/turn_metrics.jsonl\n",
            encoding="utf-8",
        )
        self._clear_caches()

    def tearDown(self):
        os.environ.pop("SHADOU_HOME", None)
        self._clear_caches()

    def _clear_caches(self):
        for fn in ("shadou.settings.get_settings",
                   "shadou.workspace.runtime_settings.load_workspace_settings_yaml",
                   "shadou.workspace.manifest.load_workspace_data"):
            try:
                mod_name, func_name = fn.rsplit(".", 1)
                import importlib
                mod = importlib.import_module(mod_name)
                getattr(mod, func_name).cache_clear()
            except Exception:
                pass

    def test_metrics_file_written_after_record(self):
        from shadou.support_runtime.metrics import record_turn_metrics
        record_turn_metrics(_make_result())
        self.assertTrue(self._metrics_file.is_file())

    def test_metrics_row_has_required_fields(self):
        from shadou.support_runtime.metrics import record_turn_metrics
        record_turn_metrics(_make_result(decision="direct_answer", confidence=0.9, tool_count=2))
        row = json.loads(self._metrics_file.read_text().strip())
        for field in ("ts", "tenant_id", "decision", "confidence", "evidence_count",
                      "verification_flagged", "tool_count", "abstained", "stale_evidence"):
            self.assertIn(field, row, f"Missing field: {field}")

    def test_no_user_message_text_in_row(self):
        from shadou.support_runtime.metrics import record_turn_metrics
        record_turn_metrics(_make_result())
        row = json.loads(self._metrics_file.read_text().strip())
        for sensitive in ("question", "answer", "text", "message", "user_text"):
            self.assertNotIn(sensitive, row)

    def test_abstained_flag_set_correctly(self):
        from shadou.support_runtime.metrics import record_turn_metrics
        record_turn_metrics(_make_result(decision="abstain"))
        row = json.loads(self._metrics_file.read_text().strip())
        self.assertTrue(row["abstained"])

    def test_non_abstain_abstained_false(self):
        from shadou.support_runtime.metrics import record_turn_metrics
        record_turn_metrics(_make_result(decision="direct_answer"))
        row = json.loads(self._metrics_file.read_text().strip())
        self.assertFalse(row["abstained"])

    def test_metrics_file_path_from_workspace(self):
        from shadou.support_runtime.metrics import _metrics_path
        p = _metrics_path()
        self.assertIn("turn_metrics.jsonl", str(p))

    def test_stale_evidence_recorded(self):
        from shadou.support_runtime.metrics import record_turn_metrics
        record_turn_metrics(_make_result(stale=True))
        row = json.loads(self._metrics_file.read_text().strip())
        self.assertTrue(row["stale_evidence"])

    def test_multiple_rows_appended(self):
        from shadou.support_runtime.metrics import record_turn_metrics
        record_turn_metrics(_make_result())
        record_turn_metrics(_make_result(decision="abstain"))
        lines = [l for l in self._metrics_file.read_text().splitlines() if l.strip()]
        self.assertEqual(len(lines), 2)


class MetricsReportTests(unittest.TestCase):
    def _rows(self, n_flagged: int = 0, n_abstained: int = 0, n_stale: int = 0, total: int = 10) -> list[dict]:
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).isoformat()
        rows = []
        for i in range(total):
            rows.append({
                "ts": ts,
                "tenant_id": "test",
                "decision": "abstain" if i < n_abstained else "direct_answer",
                "confidence": 0.8,
                "evidence_count": 1,
                "verification_flagged": i < n_flagged,
                "tool_count": 1,
                "abstained": i < n_abstained,
                "stale_evidence": i < n_stale,
            })
        return rows

    def test_report_has_required_keys(self):
        report = compute_report(self._rows(total=5))
        for key in ("total", "unverified_rate", "abstain_rate", "avg_tool_steps",
                    "stale_citation_rate", "verification_flag_rate"):
            self.assertIn(key, report)

    def test_unverified_rate_correct(self):
        report = compute_report(self._rows(n_flagged=3, total=10))
        self.assertAlmostEqual(report["unverified_rate"], 0.3)

    def test_abstain_rate_correct(self):
        report = compute_report(self._rows(n_abstained=2, total=10))
        self.assertAlmostEqual(report["abstain_rate"], 0.2)

    def test_stale_citation_rate_correct(self):
        report = compute_report(self._rows(n_stale=4, total=10))
        self.assertAlmostEqual(report["stale_citation_rate"], 0.4)

    def test_empty_rows_returns_none_rates(self):
        report = compute_report([])
        self.assertEqual(report["total"], 0)
        self.assertIsNone(report["unverified_rate"])

    def test_load_rows_filters_by_time(self):
        from datetime import datetime, timedelta, timezone
        import tempfile
        tmp = Path(tempfile.mkdtemp()) / "m.jsonl"
        now = datetime.now(timezone.utc)
        old = (now - timedelta(hours=48)).isoformat()
        recent = now.isoformat()
        tmp.write_text(
            json.dumps({"ts": old, "abstained": False, "verification_flagged": False,
                        "stale_evidence": False, "tool_count": 0}) + "\n" +
            json.dumps({"ts": recent, "abstained": False, "verification_flagged": False,
                        "stale_evidence": False, "tool_count": 0}) + "\n",
            encoding="utf-8",
        )
        since = now - timedelta(hours=24)
        rows = _load_rows(tmp, since)
        self.assertEqual(len(rows), 1)


if __name__ == "__main__":
    unittest.main()
