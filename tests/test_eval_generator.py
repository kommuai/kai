"""Phase 2-C: Synthetic eval generator."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from shadou.tools.eval_generator import generate_eval_pack, _load_corpus_map, _load_chunks


def _write_corpus_map(path: Path, intents: list[dict]) -> None:
    data = {
        "schema_version": 1,
        "compiled_at": "2026-05-31",
        "source": "master_faq",
        "intents": intents,
        "total_chunks": len(intents),
    }
    path.write_text(json.dumps(data), encoding="utf-8")


def _write_chunks(path: Path, intents: list[dict]) -> None:
    lines = []
    for i in intents:
        iid = i["intent_id"]
        alias = i["aliases"][0] if i.get("aliases") else iid
        lines.append(json.dumps({
            "source_id": f"faq:{iid}",
            "text": f"Q: {alias}\nA: Answer for {iid}.",
        }))
    path.write_text("\n".join(lines), encoding="utf-8")


def _make_intents(n: int) -> list[dict]:
    return [
        {
            "intent_id": f"intent_{i}",
            "title": f"Topic {i}",
            "aliases": [f"question about topic {i}", f"topic{i} query"],
            "chunk_count": 1,
        }
        for i in range(n)
    ]


class LoadCorpusMapTests(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp())

    def test_loads_valid_map(self):
        _write_corpus_map(self._tmp / "corpus_map.json", _make_intents(3))
        data = _load_corpus_map(self._tmp)
        self.assertIn("intents", data)
        self.assertEqual(len(data["intents"]), 3)

    def test_missing_file_returns_empty(self):
        data = _load_corpus_map(self._tmp / "nowhere")
        self.assertEqual(data, {})

    def test_loads_chunks(self):
        intents = _make_intents(2)
        _write_chunks(self._tmp / "kb_chunks.jsonl", intents)
        chunks = _load_chunks(self._tmp)
        self.assertEqual(len(chunks), 2)


class GenerateEvalPackTests(unittest.TestCase):
    def _generate(self, n: int) -> list[dict]:
        intents = _make_intents(n)
        tmp = Path(tempfile.mkdtemp())
        _write_corpus_map(tmp / "corpus_map.json", intents)
        _write_chunks(tmp / "kb_chunks.jsonl", intents)
        corpus_map = _load_corpus_map(tmp)
        chunks = _load_chunks(tmp)
        return generate_eval_pack(corpus_map, chunks)

    def test_generates_at_least_n_items_for_n_intents(self):
        items = self._generate(5)
        self.assertGreaterEqual(len(items), 5)

    def test_each_item_has_required_fields(self):
        items = self._generate(3)
        for item in items:
            for field in ("question", "expected_intent", "expected_decision", "tags", "source"):
                self.assertIn(field, item, f"Missing field: {field}")

    def test_unanswerable_items_have_abstain_decision(self):
        items = self._generate(3)
        unanswerables = [i for i in items if "unanswerable" in i["tags"]]
        self.assertGreater(len(unanswerables), 0)
        for item in unanswerables:
            self.assertEqual(item["expected_decision"], "abstain")

    def test_lookup_items_have_direct_answer_decision(self):
        items = self._generate(3)
        lookups = [i for i in items if "lookup" in i["tags"]]
        self.assertGreater(len(lookups), 0)
        for item in lookups:
            self.assertEqual(item["expected_decision"], "direct_answer")

    def test_deterministic_output(self):
        intents = _make_intents(4)
        tmp = Path(tempfile.mkdtemp())
        _write_corpus_map(tmp / "corpus_map.json", intents)
        _write_chunks(tmp / "kb_chunks.jsonl", intents)
        corpus_map = _load_corpus_map(tmp)
        chunks = _load_chunks(tmp)
        run1 = generate_eval_pack(corpus_map, chunks)
        run2 = generate_eval_pack(corpus_map, chunks)
        self.assertEqual(
            [i["question"] for i in run1],
            [i["question"] for i in run2],
        )

    def test_empty_corpus_map_returns_empty(self):
        items = generate_eval_pack({}, [])
        self.assertEqual(items, [])

    def test_source_field_is_generated(self):
        items = self._generate(2)
        for item in items:
            self.assertEqual(item["source"], "generated")

    def test_multi_intent_items_generated_for_two_plus_intents(self):
        items = self._generate(4)
        multi = [i for i in items if "multi_intent" in i["tags"]]
        self.assertGreater(len(multi), 0)

    def test_single_intent_no_multi(self):
        items = self._generate(1)
        multi = [i for i in items if "multi_intent" in i["tags"]]
        self.assertEqual(len(multi), 0)


if __name__ == "__main__":
    unittest.main()
