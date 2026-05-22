import unittest

from support_runtime.compiler import compile_canonical_knowledge
from support_runtime.providers import build_provider
from support_runtime.retrieval import HybridRetriever, SimpleReranker
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

if __name__ == "__main__":
    unittest.main()
