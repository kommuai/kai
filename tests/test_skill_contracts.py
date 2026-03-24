import unittest

from core.types import CapabilityRequest
from core.skills.workspace_factory import load_handler_class


class SkillContractTests(unittest.TestCase):
    def test_repo_reader_contract(self):
        skill = load_handler_class("repo_reader", "RepoReaderSkill")()
        req = CapabilityRequest(request_id="r1", user_id="u1", text="Read repo files", lang="EN")
        score = skill.can_handle(req, {})
        self.assertIsInstance(score, float)
        degraded = skill.degrade("x")
        self.assertFalse(degraded.ok)
        self.assertEqual(degraded.capability_used, "repo_reader")

    def test_image_diag_contract(self):
        skill = load_handler_class("image_diag", "ImageDiagnosticSkill")()
        req = CapabilityRequest(request_id="r2", user_id="u2", text="ABC12345", lang="EN")
        score = skill.can_handle(req, {})
        self.assertIsInstance(score, float)
        degraded = skill.degrade("x")
        self.assertFalse(degraded.ok)
        self.assertEqual(degraded.capability_used, "image_diag")


if __name__ == "__main__":
    unittest.main()
