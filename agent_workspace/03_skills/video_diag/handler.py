from core.skills.contracts import SkillBudget, SkillContextBundle
from core.types import CapabilityRequest, CapabilityResult


class VideoDiagnosticSkill:
    skill_id = "video_diag"
    version = "0.1.0"

    def can_handle(self, request: CapabilityRequest, context_meta: dict) -> float:
        txt = request.text.lower()
        return 0.8 if any(k in txt for k in ["video", "clip", "frame", "diagnose"]) else 0.0

    def execute(self, request: CapabilityRequest, context_bundle: SkillContextBundle, budget: SkillBudget) -> CapabilityResult:
        return CapabilityResult(
            ok=True,
            answer="Video diagnostic capability is enabled. Frame/event extraction can be attached in worker mode.",
            capability_used=self.skill_id,
            confidence=0.5,
            safety_flags=["stubbed_backend"],
        )

    def degrade(self, reason: str) -> CapabilityResult:
        return CapabilityResult(ok=False, fallback_reason=reason, capability_used=self.skill_id)
