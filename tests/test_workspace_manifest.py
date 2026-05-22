import unittest
from pathlib import Path

from kai.settings import get_settings
from kai.workspace.manifest import load_workspace_manifest, reload_workspace_manifest
from kai.workspace.tools_config import load_tools_config, reload_tools_config
from kai.workspace.validate import validate_workspace, workspace_is_healthy


class WorkspaceManifestTests(unittest.TestCase):
    def test_loads_yaml_manifest(self):
        m = reload_workspace_manifest()
        self.assertEqual(m.version, "2")
        self.assertEqual(m.tenant_id, "kommu-support")
        self.assertTrue(m.paths.knowledge_primary.endswith("master_faq.md"))

    def test_tools_yaml_loads_kommu_profile(self):
        reload_tools_config()
        cfg = load_tools_config()
        ids = {e.id for e in cfg.enabled_entries()}
        self.assertIn("search_faq", ids)
        self.assertIn("create_visitor_pass", ids)
        self.assertGreaterEqual(len(ids), 9)
        visitor = next(e for e in cfg.enabled_entries() if e.id == "create_visitor_pass")
        self.assertEqual(visitor.plugin, "smartserva_visitor_pass")

    def test_doctor_passes_on_default_workspace(self):
        issues = validate_workspace(compile_kb=True, ping_llm=False)
        self.assertTrue(workspace_is_healthy(issues), [i.message for i in issues if i.level == "error"])

    def test_manifest_resolves_paths_under_workspace(self):
        m = load_workspace_manifest()
        ws = get_settings().agent_workspace
        prompt = m.resolve(m.paths.system_prompt)
        self.assertTrue(prompt.is_file())
        self.assertEqual(prompt.parent.parent, ws)


if __name__ == "__main__":
    unittest.main()
