"""Background FAQ review scheduling (Phase 2)."""

from __future__ import annotations

import logging
import threading
from typing import Any

from config import KAI_FAQ_LEARN_ASYNC, KAI_FAQ_LEARN_ENABLED, KAI_FAQ_LEARN_ON_HANDOVER
from kai.lib.session_state import pop_human_segment_for_learn, snapshot_human_segment_for_learn
from kai.support_runtime.faq_learn import run_faq_learn

log = logging.getLogger("kai.background_review")


def _env_truthy(name: str, raw: str) -> bool:
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def schedule_faq_learn(
    user_id: str,
    *,
    trigger: str = "resume",
    pop_segment: bool = False,
) -> None:
    """Queue async FAQ learn from a human segment snapshot."""
    if not _env_truthy("KAI_FAQ_LEARN_ENABLED", KAI_FAQ_LEARN_ENABLED):
        return
    if trigger in {"handover", "escalate"} and not _env_truthy(
        "KAI_FAQ_LEARN_ON_HANDOVER", KAI_FAQ_LEARN_ON_HANDOVER
    ):
        return

    if pop_segment:
        messages, cw_id = pop_human_segment_for_learn(user_id)
    else:
        messages, cw_id = snapshot_human_segment_for_learn(user_id)
    if not messages and not cw_id:
        return

    def job() -> None:
        try:
            out = run_faq_learn(user_id, messages, cw_id, trigger=trigger)
            log.info("faq_learn trigger=%s user_id=%s %s", trigger, user_id, out)
        except Exception as exc:  # noqa: BLE001
            log.exception("faq_learn failed trigger=%s user_id=%s: %s", trigger, user_id, exc)

    if _env_truthy("KAI_FAQ_LEARN_ASYNC", KAI_FAQ_LEARN_ASYNC):
        threading.Thread(target=job, daemon=True).start()
    else:
        job()


def schedule_faq_learn_after_handback(user_id: str) -> None:
    """Resume path: pop closed human segment and review."""
    schedule_faq_learn(user_id, trigger="resume", pop_segment=True)
