"""Load and cache full master_faq.md for injection into the agent system prompt."""

from __future__ import annotations

from pathlib import Path

from config import resolve_master_faq_path

_cached_faq: str | None = None


def load_master_faq_text(*, force_reload: bool = False) -> str:
    """Return full master_faq.md body (cached until invalidate_faq_cache)."""
    global _cached_faq
    if _cached_faq is not None and not force_reload:
        return _cached_faq
    path = Path(resolve_master_faq_path())
    if path.is_file():
        _cached_faq = path.read_text(encoding="utf-8")
    else:
        _cached_faq = ""
    return _cached_faq


def invalidate_faq_cache() -> None:
    global _cached_faq
    _cached_faq = None


def master_faq_system_block() -> str:
    """System-prompt section: authoritative FAQ."""
    body = load_master_faq_text().strip()
    if not body:
        return ""
    return (
        "## Authoritative FAQ (master_faq.md)\n\n"
        "This is the **only** source of truth for Kommu product, pricing, installation, "
        "partner installers, warranty, office, and policy answers.\n"
        "- Do **not** contradict this document.\n"
        "- For policy/FAQ questions, answer from here first; paraphrase clearly and keep links verbatim.\n"
        "- Read the **full session chat** in the messages below for follow-ups (postcodes, regions, "
        "yes/no, car model already discussed).\n"
        "- **Answer the user's latest question directly**; do not default to pricing/install upsell.\n"
        "- Use tools only when this FAQ does not cover the request (official vehicle list, dongle "
        "warranty lookup, visitor pass API, bukapilot code, backlog).\n\n"
        f"{body}\n"
    )
