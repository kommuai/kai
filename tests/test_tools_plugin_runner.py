import unittest

from kai.tools_plugins.runner import _cli_flag


class PluginRunnerCliFlagTests(unittest.TestCase):
    def test_arg_aliases_map_visit_fields(self) -> None:
        params = {"arg_aliases": {"visit_date": "date", "visit_time": "time"}}
        self.assertEqual(_cli_flag("visit_date", params), "date")
        self.assertEqual(_cli_flag("visit_time", params), "time")

    def test_default_snake_to_kebab(self) -> None:
        self.assertEqual(_cli_flag("unit_id", {}), "unit-id")


if __name__ == "__main__":
    unittest.main()
