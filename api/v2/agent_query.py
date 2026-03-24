from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from core.authz.service_auth import authorize
from core.policy.settings import get_route_mode
from core.provenance.evidence import normalize_source
from core.router.engine import RouterEngine
from core.skills.workspace_factory import build_workspace_skill, get_workspace_skill_registry

router = APIRouter()


class AgentQueryRequest(BaseModel):
    user_id: str = Field(default="agent-client")
    query: str
    lang: str = Field(default="EN")


class AgentQueryResponse(BaseModel):
    answer: str
    confidence: float
    sources: list[dict]
    capability_used: str
    trace_id: str
    safety_flags: list[str]
    fallback_reason: str = ""


def _engine() -> RouterEngine:
    registry = get_workspace_skill_registry()
    skills = [build_workspace_skill(m) for m in registry.enabled_skills()]
    return RouterEngine(skills=skills, mode=get_route_mode())


@router.post("/v2/agent/query", response_model=AgentQueryResponse)
def agent_query(req: AgentQueryRequest, x_api_key: str | None = Header(default=None)):
    if not authorize(x_api_key, "public_info.read"):
        raise HTTPException(status_code=401, detail="Unauthorized service client")
    trace_id = str(uuid4())
    result = _engine().route_query(user_id=req.user_id, text=req.query, lang=req.lang)
    if not result.ok:
        raise HTTPException(status_code=404, detail=result.fallback_reason or "No answer")
    return AgentQueryResponse(
        answer=result.answer,
        confidence=result.confidence,
        sources=[normalize_source(s) for s in result.sources],
        capability_used=result.capability_used,
        trace_id=trace_id,
        safety_flags=result.safety_flags,
        fallback_reason=result.fallback_reason,
    )


@router.post("/v2/agent/search")
def agent_search(req: AgentQueryRequest, x_api_key: str | None = Header(default=None)):
    if not authorize(x_api_key, "public_info.read"):
        raise HTTPException(status_code=401, detail="Unauthorized service client")
    result = _engine().route_query(user_id=req.user_id, text=req.query, lang=req.lang)
    return {
        "trace_id": str(uuid4()),
        "capability_used": result.capability_used,
        "sources": [normalize_source(s) for s in result.sources],
        "fallback_reason": result.fallback_reason,
    }

