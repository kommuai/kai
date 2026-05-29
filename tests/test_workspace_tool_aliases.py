"""Workspace tool_aliases map tenant ids to canonical builtin handlers."""

from __future__ import annotations

import unittest
from pathlib import Path

from kai.support_runtime.tools.catalog import reload_tool_aliases, resolve_builtin_id
from kai.workspace.runtime_settings import reload_grounded_tools, reload_workspace_settings_yaml

_MINIMAL = Path(__file__).resolve().parent / "fixtures" / "minimal_workspace"
_KOMMU = Path(__file__).resolve().parent / "fixtures" / "kommu_workspace"


class WorkspaceToolAliasesTests(unittest.TestCase):
    def setUp(self) -> None:
        from tests.conftest import _apply_kai_home

        _apply_kai_home(_KOMMU)

    def test_kommu_fixture_resolves_aliases(self) -> None:
        reload_workspace_settings_yaml()
        reload_tool_aliases()
        self.assertEqual(resolve_builtin_id("search_kommu_support"), "search_official_site")
        self.assertEqual(resolve_builtin_id("lookup_warranty"), "lookup_sheet_record")
        self.assertEqual(resolve_builtin_id("read_bukapilot_file"), "read_github_file")

    def test_minimal_fixture_has_no_aliases(self) -> None:
        from tests.conftest import _apply_kai_home

        _apply_kai_home(_MINIMAL)
        reload_workspace_settings_yaml()
        reload_tool_aliases()
        self.assertEqual(reload_tool_aliases(), {})
        self.assertEqual(resolve_builtin_id("search_faq"), "search_faq")
        _apply_kai_home(_KOMMU)

    def test_kommu_grounded_tools_from_yaml(self) -> None:
        reload_workspace_settings_yaml()
        grounded = reload_grounded_tools()
        self.assertIn("search_kommu_support", grounded)
        self.assertIn("lookup_warranty", grounded)


if __name__ == "__main__":
    unittest.main()
