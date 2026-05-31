"""Phase 1-A: EvidenceItem + evidence_ledger in RuntimeResult."""
from __future__ import annotations

import json
import unittest

from shadou.support_runtime.agent_loop import AgentLoopDependencies, ReActAgentLoop
from shadou.support_runtime.models import EvidenceItem, RuntimeResult
from shadou.support_runtime.tools.registry import AgentToolRegistry
from shadou.support_runtime.retrieval import HybridRetriever, SimpleReranker


def _make_registry() -> AgentToolRegistry:
    return AgentToolRegistry(HybridRetriever(provider=None), SimpleReranker(provider=None))


class _FixedProvider:
    """LLM stub that returns a fixed JSON string."""

    def __init__(self, response: str) -> None:
        self.response = response

    def chat_messages(self, messages, temperature=0.2, max_tokens=1200) -> str:
        return self.response


class EvidenceLedgerTests(unittest.TestCase):
    def test_evidence_item_fields(self):
        ev = EvidenceItem(tool="search_faq", source_id="faq:test", snippet="some text", score=0.9)
        self.assertEqual(ev.tool, "search_faq")
        self.assertEqual(ev.source_id, "faq:test")
        self.assertEqual(ev.snippet, "some text")
        self.assertAlmostEqual(ev.score, 0.9)
        self.assertEqual(ev.support_status, "supported")

    def test_runtime_result_has_evidence_ledger(self):
        rr = RuntimeResult(decision="direct_answer", answer="hi", confidence=0.8)
        self.assertIsInstance(rr.evidence_ledger, list)
        self.assertEqual(len(rr.evidence_ledger), 0)

    def test_runtime_result_accepts_evidence_items(self):
        ev = EvidenceItem(tool="search_faq", source_id="faq:x")
        rr = RuntimeResult(decision="direct_answer", answer="hi", confidence=0.8, evidence_ledger=[ev])
        self.assertEqual(len(rr.evidence_ledger), 1)
        self.assertIsInstance(rr.evidence_ledger[0], EvidenceItem)

    def test_no_tool_calls_empty_ledger(self):
        prov = _FixedProvider('{"action":"final","decision":"direct_answer","answer":"hello","confidence":0.9}')
        loop = ReActAgentLoop(AgentLoopDependencies(provider=prov, tools=_make_registry(), system_prompt="SYS"))
        out = loop.run(text="hi")
        result = out["result"]
        self.assertIsInstance(result.evidence_ledger, list)
        self.assertEqual(len(result.evidence_ledger), 0)

    def test_tool_call_populates_ledger(self):
        # First response: call search_faq; second response: final answer
        responses = iter([
            '{"action":"tool","tool":"search_faq","args":{"query":"price"}}',
            '{"action":"final","decision":"direct_answer","answer":"The price is X.","confidence":0.85}',
        ])

        class _SeqProvider:
            def chat_messages(self, messages, temperature=0.2, max_tokens=1200):
                return next(responses)

        registry = _make_registry()
        loop = ReActAgentLoop(AgentLoopDependencies(provider=_SeqProvider(), tools=registry, system_prompt="SYS"))
        out = loop.run(text="what is the price")
        result = out["result"]
        self.assertGreaterEqual(len(result.evidence_ledger), 1)
        self.assertEqual(result.evidence_ledger[0].tool, "search_faq")

    def test_evidence_items_are_evidence_item_instances(self):
        responses = iter([
            '{"action":"tool","tool":"search_faq","args":{"query":"warranty"}}',
            '{"action":"final","decision":"direct_answer","answer":"ok","confidence":0.8}',
        ])

        class _SeqProvider:
            def chat_messages(self, messages, temperature=0.2, max_tokens=1200):
                return next(responses)

        loop = ReActAgentLoop(AgentLoopDependencies(
            provider=_SeqProvider(), tools=_make_registry(), system_prompt="SYS"
        ))
        out = loop.run(text="warranty")
        for ev in out["result"].evidence_ledger:
            self.assertIsInstance(ev, EvidenceItem)


if __name__ == "__main__":
    unittest.main()
