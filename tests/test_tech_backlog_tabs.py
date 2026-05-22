import unittest

from kai.support_runtime.tech_backlog import list_backlog_sheet_tabs


class TechBacklogTabsTests(unittest.TestCase):
    def test_list_tabs_returns_list(self):
        tabs = list_backlog_sheet_tabs()
        self.assertIsInstance(tabs, list)


if __name__ == "__main__":
    unittest.main()
