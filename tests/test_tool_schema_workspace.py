import os
import unittest
from pathlib import Path
from unittest.mock import patch

from kai.support_runtime.tools.registry import AgentToolRegistry
from kai.support_runtime.retrieval import HybridRetriever, SimpleReranker
from kai.workspace.tools_config import reload_tools_config


class ToolSchemaWorkspaceTests(unittest.TestCase):
    def test_workspace_yaml_schema_overrides_catalog(self) -> None:
        fixture = Path(__file__).resolve().parent / "fixtures" / "kommu_workspace"
        with patch.dict(os.environ, {"KAI_HOME": str(fixture)}, clear=False):
            reload_tools_config()
            reg = AgentToolRegistry(HybridRetriever(provider=None), SimpleReranker(provider=None))
            schemas = {s["name"]: s["schema"] for s in reg.list_schemas()}
            self.assertIn("reason", schemas["escalate_to_human"]["properties"])
            self.assertIn("query", schemas["search_faq"]["properties"])


if __name__ == "__main__":
    unittest.main()
