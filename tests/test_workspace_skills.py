import unittest

from shadou.support_runtime.compiler import compile_canonical_knowledge


class CompiledKnowledgeTests(unittest.TestCase):
    def test_compiled_intents_load_for_current_runtime(self):
        counts = compile_canonical_knowledge()
        self.assertGreater(counts["intents"], 0)
        self.assertGreater(counts["chunks"], 0)


if __name__ == "__main__":
    unittest.main()
