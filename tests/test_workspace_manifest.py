import os
import unittest
from pathlib import Path

from shadou.settings import get_settings
from shadou.workspace.manifest import load_workspace_manifest, reload_workspace_manifest
from shadou.workspace.tools_config import load_tools_config, reload_tools_config
from shadou.workspace.validate import validate_workspace, workspace_is_healthy


class WorkspaceManifestTests(unittest.TestCase):
    def setUp(self):
        minimal = Path(__file__).resolve().parent / "fixtures" / "minimal_workspace"
        os.environ["SHADOU_HOME"] = str(minimal)
        os.environ.pop("AGENT_WORKSPACE", None)
        from shadou.settings import reload_settings

        reload_settings()
        reload_workspace_manifest()

    def test_loads_yaml_manifest(self):
        m = reload_workspace_manifest()
        self.assertEqual(m.version, "2")
        self.assertEqual(m.tenant_id, "generic-support")
        self.assertTrue(m.paths.knowledge_primary.endswith("master_faq.md"))

    def test_tools_yaml_loads_minimal_profile(self):
        reload_tools_config()
        cfg = load_tools_config()
        ids = {e.id for e in cfg.enabled_entries()}
        self.assertIn("search_faq", ids)
        self.assertIn("escalate_to_human", ids)
        self.assertGreaterEqual(len(ids), 3)

    def test_doctor_passes_on_default_workspace(self):
        issues = validate_workspace(compile_kb=True, ping_llm=False)
        self.assertTrue(workspace_is_healthy(issues), [i.message for i in issues if i.level == "error"])

    def test_manifest_resolves_paths_under_workspace(self):
        m = load_workspace_manifest()
        home = get_settings().shadou_home
        prompt = m.resolve(m.paths.system_prompt)
        self.assertTrue(prompt.is_file())
        self.assertEqual(prompt.parent, home)


if __name__ == "__main__":
    unittest.main()
