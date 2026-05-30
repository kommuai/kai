"""Parse structured master_faq.md schema and maintain SOP doc sync region."""
from __future__ import annotations

import re
from typing import Any

SOP_SYNC_START_DEFAULT = "<!-- sop-sync:start -->"
SOP_SYNC_END_DEFAULT = "<!-- sop-sync:end -->"

_SCHEMA_HEADER_RE = re.compile(
    r"^##\s+(intent|workflow|data|dynamic)\s*:\s*([A-Za-z0-9_\-./]+)\s*$"
)
_INTENT_HEADER_RE = re.compile(r"^##\s+intent\s*:\s*([A-Za-z0-9_\-./]+)\s*$", re.IGNORECASE)


def safe_intent_id(intent_id: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_\-./]+", (intent_id or "").strip()))


def normalize_intent_block(intent_id: str, content: str) -> str:
    """Return a full `## intent:` block (aliases + answer) for intent_id."""
    iid = (intent_id or "").strip()
    if not safe_intent_id(iid):
        raise ValueError(f"Invalid intent_id: {intent_id!r}")
    body = (content or "").strip()
    if not body:
        raise ValueError(f"Empty content for intent '{iid}'")
    if _INTENT_HEADER_RE.match(body.splitlines()[0].strip()):
        probe = body
    else:
        probe = f"## intent: {iid}\n{body}"
    parsed = parse_master_faq_schema(probe)
    intents = parsed.get("intents") or []
    if not intents:
        raise ValueError(f"Could not parse intent block for '{iid}'")
    row = intents[0]
    if (row.get("intent_id") or "").strip() != iid:
        raise ValueError(f"Intent header id does not match intent_id '{iid}'")
    return render_master_faq_schema({"intents": [row], "workflows": [], "data": [], "dynamic": []}).strip()


def upsert_intent_block(full_text: str, intent_id: str, content: str) -> str:
    """Replace or append one intent section in master_faq.md."""
    new_block = normalize_intent_block(intent_id, content)
    text = (full_text or "").replace("\r\n", "\n")
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    replaced = False
    while i < len(lines):
        line = lines[i]
        m = _INTENT_HEADER_RE.match(line.strip())
        if m and m.group(1) == intent_id:
            replaced = True
            i += 1
            while i < len(lines) and not _SCHEMA_HEADER_RE.match(lines[i].strip()):
                i += 1
            if out and out[-1].strip():
                out.append("")
            out.extend(new_block.split("\n"))
            out.append("")
            continue
        out.append(line)
        i += 1
    merged = "\n".join(out).rstrip()
    if replaced:
        return merged + "\n"
    return _append_intent_block(merged, new_block)


def _append_intent_block(text: str, new_block: str) -> str:
    end_marker = SOP_SYNC_END_DEFAULT
    block = new_block.strip()
    if end_marker in text:
        before, after = text.split(end_marker, 1)
        before = before.rstrip()
        if before and not before.endswith("\n"):
            before += "\n"
        return f"{before}\n\n{block}\n\n{end_marker}{after}"
    base = text.rstrip()
    if base:
        return f"{base}\n\n{block}\n"
    return f"{block}\n"


def _split_schema_blocks(text: str) -> list[tuple[str, str, str]]:
    lines = (text or "").replace("\r\n", "\n").split("\n")
    out: list[tuple[str, str, str]] = []
    cur_kind = ""
    cur_name = ""
    cur_body: list[str] = []
    for line in lines:
        m = _SCHEMA_HEADER_RE.match(line.strip())
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
            if kind == "data":
                sections["data"].append({"name": name, "fields": kv})
            else:
                dyn: dict[str, Any] = {"name": name, "fields": kv}
                pst = (kv.get("priority") or "").strip()
                try:
                    dyn["priority"] = int(pst) if pst else 0
                except ValueError:
                    dyn["priority"] = 0
                vf = (kv.get("valid_from") or "").strip()
                vu = (kv.get("valid_until") or "").strip()
                dyn["valid_from"] = vf or None
                dyn["valid_until"] = vu or None
                sections["dynamic"].append(dyn)
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


def render_master_faq_schema(schema: dict[str, list[dict[str, Any]]], *, trailing_blank: bool = True) -> str:
    """Render structured FAQ schema blocks back to markdown."""
    blocks: list[str] = []

    for row in schema.get("intents", []):
        intent_id = (row.get("intent_id") or "").strip()
        answer = (row.get("answer") or "").strip()
        if not intent_id or not answer:
            continue
        aliases = [str(a).strip() for a in (row.get("aliases") or []) if str(a).strip()]
        parts = [f"## intent: {intent_id}", "aliases:"]
        parts.extend(f"- {a}" for a in aliases)
        parts.append("answer:")
        parts.append(answer)
        blocks.append("\n".join(parts))

    for row in schema.get("workflows", []):
        workflow_id = (row.get("workflow_id") or "").strip()
        steps = [str(s).strip() for s in (row.get("steps") or []) if str(s).strip()]
        if not workflow_id or not steps:
            continue
        parts = [f"## workflow: {workflow_id}", "steps:"]
        parts.extend(f"{i}. {step}" for i, step in enumerate(steps, start=1))
        blocks.append("\n".join(parts))

    for row in schema.get("data", []):
        name = (row.get("name") or "").strip()
        fields = row.get("fields") or {}
        if not name or not isinstance(fields, dict) or not fields:
            continue
        parts = [f"## data: {name}"]
        for k, v in fields.items():
            parts.append(f"{k}: {v}")
        blocks.append("\n".join(parts))

    for row in schema.get("dynamic", []):
        name = (row.get("name") or "").strip()
        fields = row.get("fields") or {}
        if not name or not isinstance(fields, dict) or not fields:
            continue
        parts = [f"## dynamic: {name}"]
        for k, v in fields.items():
            parts.append(f"{k}: {v}")
        blocks.append("\n".join(parts))

    out = "\n\n".join(blocks)
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
