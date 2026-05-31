import unittest
from unittest.mock import patch


class RefreshRuntimeTests(unittest.TestCase):
    @patch("shadou.services.container.get_shadou_service")
    @patch("shadou.services.container.get_support_runtime_service")
    @patch("shadou.workspace.reload.reload_workspace_caches")
    def test_refresh_calls_startup(self, reload_mock, runtime_mock, _shadou_mock):
        from shadou.engine.refresh import refresh_runtime_knowledge

        runtime = runtime_mock.return_value
        runtime.startup.return_value = {"chunks": 1}
        out = refresh_runtime_knowledge(compile_kb=True)
        reload_mock.assert_called_once()
        runtime.startup.assert_called_once()
        self.assertTrue(out.get("ok"))


if __name__ == "__main__":
    unittest.main()
