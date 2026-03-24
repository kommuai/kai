"""Parse structured master_faq.md schema and maintain SOP doc sync region."""
from __future__ import annotations

import re
from typing import Any

SOP_SYNC_START_DEFAULT = "<!-- sop-sync:start -->"
SOP_SYNC_END_DEFAULT = "<!-- sop-sync:end -->"


def _split_schema_blocks(text: str) -> list[tuple[str, str, str]]:
    lines = (text or "").replace("\r\n", "\n").split("\n")
    header_re = re.compile(r"^##\s+(intent|workflow|data|dynamic)\s*:\s*([A-Za-z0-9_\-./]+)\s*$")
    out: list[tuple[str, str, str]] = []
    cur_kind = ""
    cur_name = ""
    cur_body: list[str] = []
    for line in lines:
        m = header_re.match(line.strip())
        if m:
            if cur_kind:
                out.append((cur_kind, cur_name, "\n".join(cur_body).strip()))
            cur_kind = m.group(1).strip()
            cur_name = m.group(2).strip()
            cur_body = []
            continue
        if cur_kind:
            cur_body.append(line)
    if cur_kind:
        out.append((cur_kind, cur_name, "\n".join(cur_body).strip()))
    return out


def parse_master_faq_schema(text: str) -> dict[str, list[dict[str, Any]]]:
    if not text or not text.strip():
        return {"intents": [], "workflows": [], "data": [], "dynamic": []}
    sections = {"intents": [], "workflows": [], "data": [], "dynamic": []}
    for kind, name, body in _split_schema_blocks(text):
        if kind == "intent":
            aliases: list[str] = []
            answer_lines: list[str] = []
            mode = ""
            for ln in body.splitlines():
                raw = ln.rstrip()
                s = raw.strip()
                if not s:
                    if mode == "answer":
                        answer_lines.append("")
                    continue
                if s == "aliases:":
                    mode = "aliases"
                    continue
                if s == "answer:":
                    mode = "answer"
                    continue
                if mode == "aliases" and s.startswith("- "):
                    aliases.append(s[2:].strip())
                elif mode == "answer":
                    answer_lines.append(raw)
            answer = "\n".join(answer_lines).strip()
            if not answer:
                raise ValueError(f"Invalid intent block '{name}': missing answer")
            sections["intents"].append({"intent_id": name, "aliases": aliases, "answer": answer})
        elif kind == "workflow":
            steps: list[str] = []
            in_steps = False
            for ln in body.splitlines():
                s = ln.strip()
                if s == "steps:":
                    in_steps = True
                    continue
                if in_steps and re.match(r"^\d+\.\s+.+$", s):
                    steps.append(re.sub(r"^\d+\.\s+", "", s))
            if not steps:
                raise ValueError(f"Invalid workflow block '{name}': missing steps")
            sections["workflows"].append({"workflow_id": name, "steps": steps})
        else:
            kv: dict[str, str] = {}
            for ln in body.splitlines():
                s = ln.strip()
                if not s or s.startswith("---"):
                    continue
                if ":" not in s:
                    continue
                k, v = s.split(":", 1)
                kv[k.strip()] = v.strip()
            if not kv:
                raise ValueError(f"Invalid {kind} block '{name}': missing key-values")
            sections["data" if kind == "data" else "dynamic"].append({"name": name, "fields": kv})
    return sections


def parse_faq_markdown(text: str) -> list[dict[str, str]]:
    """Compatibility helper: produce Q/A list from strict intent blocks only."""
    schema = parse_master_faq_schema(text)
    out = []
    for row in schema["intents"]:
        q = (row.get("aliases") or [row["intent_id"]])[0]
        out.append({"question": q, "answer": row["answer"]})
    return out


def render_qas_markdown(qas: list[dict[str, Any]], *, trailing_blank: bool = True) -> str:
    parts: list[str] = []
    for item in qas:
        q = (item.get("question") or "").strip()
        a = (item.get("answer") or "").strip()
        if not q or not a:
            continue
        slug = re.sub(r"[^a-z0-9]+", "_", q.lower()).strip("_")[:80] or "intent_generated"
        parts.append(f"## intent: {slug}\naliases:\n- {q}\nanswer:\n{a}")
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
