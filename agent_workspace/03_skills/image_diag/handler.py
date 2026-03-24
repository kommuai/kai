from core.skills.contracts import SkillBudget, SkillContextBundle
from core.types import CapabilityRequest, CapabilityResult


class ImageDiagnosticSkill:
    skill_id = "image_diag"
    version = "0.1.0"

    def can_handle(self, request: CapabilityRequest, context_meta: dict) -> float:
        txt = request.text.lower()
        return 0.8 if any(k in txt for k in ["image", "photo", "picture", "diagnose"]) else 0.0

    def execute(self, request: CapabilityRequest, context_bundle: SkillContextBundle, budget: SkillBudget) -> CapabilityResult:
        return CapabilityResult(
            ok=True,
            answer="Image diagnostic capability is enabled. Upload handling and model backend can be attached in worker mode.",
            capability_used=self.skill_id,
            confidence=0.5,
            safety_flags=["stubbed_backend"],
        )

    def degrade(self, reason: str) -> CapabilityResult:
        return CapabilityResult(ok=False, fallback_reason=reason, capability_used=self.skill_id)
