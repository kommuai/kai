import logging
import time
import uuid

from core.policy.settings import RouteMode
from core.policy.tool_adapter import ToolAdapter
from core.skills.contracts import Skill, SkillBudget, SkillContextBundle
from core.types import CapabilityRequest, CapabilityResult

log = logging.getLogger("kai.router")


class RouterEngine:
    def __init__(self, skills: list[Skill], mode: RouteMode):
        self.skills = skills
        self.mode = mode
        self.adapter = ToolAdapter()

    def route_query(self, user_id: str, text: str, lang: str = "EN") -> CapabilityResult:
        req = CapabilityRequest(
            request_id=str(uuid.uuid4()),
            user_id=user_id,
            text=text,
            lang=lang,
        )
        meta: dict[str, str] = {"route_mode": self.mode.value}
        ranked = sorted(
            ((s, s.can_handle(req, meta)) for s in self.skills),
            key=lambda t: t[1],
            reverse=True,
        )

        start = time.time()
        for skill, score in ranked:
            if score <= 0:
                continue
            try:
                out = self.adapter.execute(
                    name=getattr(skill, "skill_id", "unknown_skill"),
                    fn=lambda: skill.execute(req, SkillContextBundle(), SkillBudget()),
                )
                out.metadata["route_mode"] = self.mode.value
                out.metadata["candidate_score"] = score
                out.metadata["latency_ms"] = int((time.time() - start) * 1000)
                if out.ok:
                    return out
            except Exception as exc:  # noqa: BLE001
                log.warning("[Router] skill=%s failed err=%s", getattr(skill, "skill_id", "unknown"), exc)
        return CapabilityResult(
            ok=False,
            answer="",
            fallback_reason="no_skill_success",
            metadata={"route_mode": self.mode.value, "latency_ms": int((time.time() - start) * 1000)},
        )

