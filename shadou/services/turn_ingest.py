"""Single entry for per-turn session writes (summary, facts, optional history)."""

from __future__ import annotations

from shadou.lib.session_state import (
    add_message_to_history,
    extract_and_store_facts,
    update_session_summary,
)


def ingest_user_turn(
    user_id: str,
    text: str,
    *,
    record_history: bool,
    source: str = "user",
) -> None:
    """Record a user message into session state.

    pre_router uses record_history=False (history appended on bot path in execute).
    execute uses record_history=True for the user line before ReAct.
    """
    if not user_id or not (text or "").strip():
        return
    update_session_summary(user_id, "user", text)
    extract_and_store_facts(user_id, text, source=source)
    if record_history:
        add_message_to_history(user_id, "user", text)
