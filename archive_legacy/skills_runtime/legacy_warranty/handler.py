from core.skills.contracts import SkillBudget, SkillContextBundle
from core.types import CapabilityRequest, CapabilityResult
from google_sheets import warranty_lookup_by_dongle, warranty_text_from_row


class LegacyWarrantySkill:
    skill_id = "legacy_warranty"
    version = "1.0.0"

    def can_handle(self, request: CapabilityRequest, context_meta: dict) -> float:
        if 6 <= len(request.text.strip()) <= 20:
            return 0.9
        return 0.0

    def execute(self, request: CapabilityRequest, context_bundle: SkillContextBundle, budget: SkillBudget) -> CapabilityResult:
        row = warranty_lookup_by_dongle(request.text.strip())
        if not row:
            return self.degrade("warranty_not_found")
        answer = f"Warranty status: {warranty_text_from_row(row)}" if request.lang == "EN" else f"Status waranti: {warranty_text_from_row(row)}"
        return CapabilityResult(
            ok=True,
            answer=answer,
            capability_used=self.skill_id,
            confidence=0.95,
            sources=[{"source_type": "warranty_sheet", "path": "WARRANTY_CSV_URL", "retrieval_score": 1.0}],
        )

    def degrade(self, reason: str) -> CapabilityResult:
        return CapabilityResult(ok=False, fallback_reason=reason, capability_used=self.skill_id)

