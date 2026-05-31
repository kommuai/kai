"""Load and cache full master_faq.md for injection into the agent system prompt."""

from __future__ import annotations

from pathlib import Path

from shadou.settings import get_settings

_cached_faq: str | None = None


def load_master_faq_text(*, force_reload: bool = False) -> str:
    global _cached_faq
    if _cached_faq is not None and not force_reload:
        return _cached_faq
    path = get_settings().resolve_master_faq_path()
    if path.is_file():
        _cached_faq = path.read_text(encoding="utf-8")
    else:
        _cached_faq = ""
    return _cached_faq


def invalidate_faq_cache() -> None:
    global _cached_faq
    _cached_faq = None


def master_faq_system_block() -> str:
    from shadou.workspace.manifest import load_workspace_manifest

    manifest = load_workspace_manifest()
    if manifest.knowledge.inject_mode == "retrieval_first":
        return (
            "## Knowledge base\n\n"
            "Product and policy **facts** live in **master_faq.md** (compiled chunks). "
            "Call **search_faq** before stating them — see **system_prompt.md** for when and how. "
            "Do not invent facts from general knowledge.\n"
        )

    body = load_master_faq_text().strip()
    if not body:
        return ""
    custom = (manifest.knowledge.faq_preamble or "").strip()
    if custom:
        preamble = custom if custom.endswith("\n") else custom + "\n"
    else:
        preamble = (
            "## Authoritative FAQ (master_faq.md)\n\n"
            "This is the **only** source of truth for product, pricing, installation, "
            "warranty, office, and policy answers.\n"
            "- Do **not** contradict this document.\n"
            "- For policy/FAQ questions, answer from here first; paraphrase clearly and keep links verbatim.\n"
            "- Read the **full session chat** in the messages below for follow-ups.\n"
            "- Use tools when this FAQ does not cover the request.\n\n"
        )
    return f"{preamble}{body}\n"
