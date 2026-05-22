import unittest

from kai.core.context.registry import ContextRegistry


class ContextRegistryTests(unittest.TestCase):
    def test_load_yaml_registry(self):
        reg = ContextRegistry()
        data = reg.load()
        self.assertTrue(isinstance(data, dict))
        self.assertIn("default_contexts", data)


if __name__ == "__main__":
    unittest.main()
