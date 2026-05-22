import unittest
from unittest.mock import patch


class StartupSingleCompileTests(unittest.TestCase):
    @patch("kai.support_runtime.service.compile_canonical_knowledge", return_value={"chunks": 10, "intents": 9})
    def test_run_startup_compiles_once(self, compile_mock):
        from kai.engine.startup import run_startup

        out = run_startup(compile_kb=True)
        self.assertEqual(compile_mock.call_count, 1)
        self.assertTrue(out.get("compile_kb"))


if __name__ == "__main__":
    unittest.main()
