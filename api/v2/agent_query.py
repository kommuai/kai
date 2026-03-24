from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from core.authz.service_auth import authorize
from core.provenance.evidence import normalize_source
from services.container import support_runtime_service

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

@router.post("/v2/agent/query", response_model=AgentQueryResponse)
def agent_query(req: AgentQueryRequest, x_api_key: str | None = Header(default=None)):
    if not authorize(x_api_key, "public_info.read"):
        raise HTTPException(status_code=401, detail="Unauthorized service client")
    trace_id = str(uuid4())
    result = support_runtime_service.execute(text=req.query, lang=req.lang, user_id=req.user_id)
    if result.decision == "escalate_human":
        raise HTTPException(status_code=404, detail=result.fallback_reason or "Escalation required")
    return AgentQueryResponse(
        answer=result.answer,
        confidence=result.confidence,
        sources=[normalize_source({"source_type": "kb", "path": sid}) for sid in result.source_ids],
        capability_used=result.capability_used or "support_runtime",
        trace_id=trace_id,
        safety_flags=[],
        fallback_reason=result.fallback_reason,
    )


@router.post("/v2/agent/search")
def agent_search(req: AgentQueryRequest, x_api_key: str | None = Header(default=None)):
    if not authorize(x_api_key, "public_info.read"):
        raise HTTPException(status_code=401, detail="Unauthorized service client")
    result = support_runtime_service.execute(text=req.query, lang=req.lang, user_id=req.user_id)
    return {
        "trace_id": str(uuid4()),
        "capability_used": result.capability_used or "support_runtime",
        "sources": [normalize_source({"source_type": "kb", "path": sid}) for sid in result.source_ids],
        "fallback_reason": result.fallback_reason,
    }

