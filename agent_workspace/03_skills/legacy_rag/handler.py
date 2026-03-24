from core.skills.contracts import SkillBudget, SkillContextBundle
from core.types import CapabilityRequest, CapabilityResult
from services.container import kai_service


class LegacyRagSkill:
    skill_id = "legacy_rag"
    version = "1.0.0"

    def can_handle(self, request: CapabilityRequest, context_meta: dict) -> float:
        txt = request.text.lower()
        if any(k in txt for k in ["support", "ka2", "kommu", "warranty", "cars", "compatible"]):
            return 0.8
        return 0.4

    def execute(self, request: CapabilityRequest, context_bundle: SkillContextBundle, budget: SkillBudget) -> CapabilityResult:
        answer = kai_service.run_rag_dual(request.text, lang_hint=request.lang, user_id=request.user_id)
        if not answer:
            return self.degrade("empty_rag_answer")
        return CapabilityResult(
            ok=True,
            answer=answer,
            capability_used=self.skill_id,
            confidence=0.75,
            sources=[{"source_type": "sop", "path": "rag/sop_data.json", "retrieval_score": 0.75}],
        )

    def degrade(self, reason: str) -> CapabilityResult:
        return CapabilityResult(ok=False, fallback_reason=reason, capability_used=self.skill_id)
