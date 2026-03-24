import unittest

from config import AGENT_WORKSPACE
from core.skills.workspace_registry import WorkspaceSkillRegistry


class WorkspaceSkillRegistryTests(unittest.TestCase):
    def test_loads_workspace_skills(self):
        reg = WorkspaceSkillRegistry(f"{AGENT_WORKSPACE}/03_skills")
        data = reg.load()
        self.assertIn("legacy_rag", data)
        self.assertIn("repo_reader", data)
        enabled = {m.skill_id for m in reg.enabled_skills()}
        self.assertIn("legacy_rag", enabled)


if __name__ == "__main__":
    unittest.main()
