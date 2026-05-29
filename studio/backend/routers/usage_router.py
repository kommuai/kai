"""DeepSeek token usage and USD cost for Studio dashboard."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from llm_usage_service import get_deepseek_usage_summary
from models import User
from schemas import DeepSeekUsageSummaryOut

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/deepseek", response_model=DeepSeekUsageSummaryOut)
def deepseek_usage(
    period: str = Query("day", pattern="^(day|month)$"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_deepseek_usage_summary(db, user.id, period=period)
