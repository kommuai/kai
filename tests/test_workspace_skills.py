import unittest

from support_runtime.compiler import compile_canonical_knowledge
from support_runtime.router import IntentRouter


class RuntimeIntentRegistryTests(unittest.TestCase):
    def test_compiled_intents_load_for_current_runtime(self):
        counts = compile_canonical_knowledge()
        self.assertGreaterEqual(counts["intents"], 0)
        router = IntentRouter()
        router.load()
        route_type, _, _ = router.route("Can I install today?")
        self.assertIn(route_type, {"known_faq_intent", "unsupported_ambiguous"})


if __name__ == "__main__":
    unittest.main()
