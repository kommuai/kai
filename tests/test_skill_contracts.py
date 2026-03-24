import unittest

from support_runtime.compiler import compile_canonical_knowledge
from support_runtime.providers import build_provider
from support_runtime.retrieval import HybridRetriever, SimpleReranker
from support_runtime.tools import ToolPolicyEngine


class SkillContractTests(unittest.TestCase):
    def test_retriever_and_reranker_contract(self):
        compile_canonical_knowledge()
        provider = build_provider()
        retriever = HybridRetriever(provider=provider)
        retriever.load()
        items = retriever.retrieve("installation support", top_k=3)
        self.assertIsInstance(items, list)
        reranker = SimpleReranker(provider=provider)
        ranked = reranker.rerank("installation support", items, top_k=2)
        self.assertIsInstance(ranked, list)

    def test_tool_policy_contract(self):
        engine = ToolPolicyEngine()
        engine.load()
        tool_name, required = engine.decide("account_order_status_intent", "is my order shipped")
        self.assertIsInstance(tool_name, str)
        self.assertIsInstance(required, list)


if __name__ == "__main__":
    unittest.main()
