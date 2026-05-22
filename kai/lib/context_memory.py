"""Build per-turn memory block for the ReAct loop (Hermes-style user-message injection)."""

from __future__ import annotations

from kai.lib.session_state import build_short_term_context, get_session_topics


def build_turn_memory_block(user_id: str, *, extra: str = "") -> str:
    """Memory injected into the current user turn (not the cached system prompt).

    `extra` may hold authoritative FAQ hints from canonical lookup.
    """
    if not user_id:
        return (extra or "").strip()

    parts: list[str] = []
    core = build_short_term_context(user_id)
    if core:
        parts.append(core)

    topics = get_session_topics(user_id)
    topic_lines: list[str] = []
    if topics.get("last_topic"):
        topic_lines.append(f"- Active topic: {topics['last_topic']}")
    if topics.get("last_vehicle"):
        line = f"- Vehicle in thread: {topics['last_vehicle']}"
        if topics.get("last_vehicle_year"):
            line += f" (year {topics['last_vehicle_year']})"
        topic_lines.append(line)
    if topics.get("last_dongle"):
        topic_lines.append(f"- Dongle ID mentioned: {topics['last_dongle']}")
    if topic_lines:
        parts.append(
            "### Topic stickiness (do not re-ask)\n"
            + "\n".join(topic_lines)
        )

    extra = (extra or "").strip()
    if extra:
        parts.append(extra)

    if not parts:
        return ""
    return (
        "<kai-session-context>\n"
        + "\n\n".join(parts)
        + "\n</kai-session-context>"
    )
