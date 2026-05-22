"""Canonical FAQ shared between FAQ-first shelf and ReAct loop."""

from __future__ import annotations

import unittest

from kai.support_runtime.agent_tools import AgentToolRegistry
from kai.support_runtime.canonical_faq import (
    extract_answer_from_chunk,
    format_canonical_hint,
    pick_best_canonical,
    pick_faq_first_runtime,
)
from kai.support_runtime.retrieval import HybridRetriever, SimpleReranker


class CanonicalFaqUnitTests(unittest.TestCase):
    def test_extract_answer_from_chunk(self):
        text = "Q: install\nA: Use the video: https://youtu.be/abc"
        self.assertIn("youtu.be", extract_answer_from_chunk(text))

    def test_pick_faq_first_requires_url_when_link_intent(self):
        payload = {
            "results": [
                {
                    "source_id": "faq:pricing",
                    "text": "Q: price\nA: RM4999",
                    "canonical_answer": "RM4999",
                    "score": 0.9,
                    "metadata": {"category": "known_faq_intent", "intent_id": "pricing"},
                }
            ]
        }
        self.assertIsNone(pick_faq_first_runtime(payload, wants_video=False, wants_link=True))
        payload["results"][0]["canonical_answer"] = "Guide: https://youtu.be/abc"
        hit = pick_faq_first_runtime(payload, wants_video=True, wants_link=True)
        self.assertIsNotNone(hit)
        self.assertIn("youtu", hit["canonical_answer"])

    def test_pick_best_canonical_for_react_no_url_required(self):
        payload = {
            "results": [
                {
                    "source_id": "faq:office",
                    "text": "Q: hours\nA: Mon-Fri 10-6",
                    "canonical_answer": "Mon-Fri 10-6",
                    "score": 0.55,
                    "metadata": {"category": "known_faq_intent", "intent_id": "office_info"},
                }
            ]
        }
        hit = pick_best_canonical(payload)
        self.assertEqual(hit["intent_id"], "office_info")

    def test_format_hint_includes_answer(self):
        h = format_canonical_hint(
            {"intent_id": "self_install", "canonical_answer": "Video: https://x", "source_id": "faq:self_install", "score": 0.8}
        )
        self.assertIn("Authoritative FAQ", h)
        self.assertIn("https://x", h)


class SearchFaqCanonicalFieldTests(unittest.TestCase):
    def test_search_faq_returns_canonical_answer_fields(self):
        reg = AgentToolRegistry(HybridRetriever(provider=None), SimpleReranker(provider=None))
        out = reg.search_faq(query="office hours")
        self.assertTrue(out.get("ok"))
        if out.get("results"):
            row = out["results"][0]
            self.assertIn("canonical_answer", row)
            self.assertTrue(row.get("canonical_answer") or row.get("text"))


if __name__ == "__main__":
    unittest.main()
