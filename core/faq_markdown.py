"""Parse FAQ from master_faq.md (## headings) and maintain SOP doc sync region."""
from __future__ import annotations

import re
from typing import Any

SOP_SYNC_START_DEFAULT = "<!-- sop-sync:start -->"
SOP_SYNC_END_DEFAULT = "<!-- sop-sync:end -->"


def parse_faq_markdown(text: str) -> list[dict[str, str]]:
    """Split markdown on `## ` headings; each block is question (title) + answer (body)."""
    if not text or not text.strip():
        return []
    lines = text.replace("\r\n", "\n").split("\n")
    blocks: list[tuple[str, list[str]]] = []
    current_title: str | None = None
    current_body: list[str] = []

    heading_re = re.compile(r"^##\s+(.+?)\s*$")

    for line in lines:
        m = heading_re.match(line)
        if m:
            if current_title is not None:
                body = "\n".join(current_body).strip()
                if current_title and body:
                    blocks.append((current_title, body))
            current_title = m.group(1).strip()
            current_body = []
            continue
        if current_title is not None:
            current_body.append(line)

    if current_title is not None:
        body = "\n".join(current_body).strip()
        if current_title and body:
            blocks.append((current_title, body))

    return [{"question": q, "answer": a} for q, a in blocks]


def render_qas_markdown(qas: list[dict[str, Any]], *, trailing_blank: bool = True) -> str:
    parts: list[str] = []
    for item in qas:
        q = (item.get("question") or "").strip()
        a = (item.get("answer") or "").strip()
        if not q or not a:
            continue
        parts.append(f"## {q}\n\n{a}")
    out = "\n\n".join(parts)
    if trailing_blank and out:
        out += "\n"
    return out


def replace_sop_sync_region(
    full_text: str,
    inner_markdown: str,
    start_marker: str = SOP_SYNC_START_DEFAULT,
    end_marker: str = SOP_SYNC_END_DEFAULT,
) -> str:
    """Replace content between markers with inner_markdown (trimmed). Preserves markers."""
    if start_marker not in full_text or end_marker not in full_text:
        return full_text
    before, rest = full_text.split(start_marker, 1)
    _, after = rest.split(end_marker, 1)
    inner = inner_markdown.strip()
    if inner and not inner.endswith("\n"):
        inner += "\n"
    return f"{before}{start_marker}\n{inner}{end_marker}{after}"


def ensure_sop_sync_markers(
    full_text: str,
    start_marker: str = SOP_SYNC_START_DEFAULT,
    end_marker: str = SOP_SYNC_END_DEFAULT,
) -> str:
    """If markers missing, append an empty sync region at end."""
    if start_marker in full_text and end_marker in full_text:
        return full_text
    suffix = f"\n\n{start_marker}\n\n{end_marker}\n"
    return full_text.rstrip() + suffix
