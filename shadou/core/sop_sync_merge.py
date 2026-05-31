from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any

import pytz

from shadou.settings import get_settings
from shadou.core.faq_markdown import (
    SOP_SYNC_END_DEFAULT,
    SOP_SYNC_START_DEFAULT,
    ensure_sop_sync_markers,
    parse_master_faq_schema,
    render_master_faq_schema,
    replace_sop_sync_region,
)
from shadou.lib.sop_doc_loader import fetch_sop_sync_region_from_google_doc
from shadou.support_runtime.sop_writeback import push_master_faq_to_google_doc

def _master_faq_path() -> Path:
    return get_settings().resolve_master_faq_path()


def _state_path() -> Path:
    return get_settings().sop_sync_state_path


def _tz_region() -> str:
    return get_settings().tz_region


def state_path() -> Path:
    """Public accessor for scheduler/tests."""
    return _state_path()


def _extract_local_sync_region(full_text: str) -> str:
    if SOP_SYNC_START_DEFAULT not in full_text or SOP_SYNC_END_DEFAULT not in full_text:
        return ""
    start = full_text.index(SOP_SYNC_START_DEFAULT) + len(SOP_SYNC_START_DEFAULT)
    end = full_text.index(SOP_SYNC_END_DEFAULT, start)
    return full_text[start:end].strip("\n")


def read_local_region() -> str:
    path = _master_faq_path()
    if not path.exists():
        return ""
    return _extract_local_sync_region(path.read_text(encoding="utf-8"))


def pull_google_region() -> str:
    return (fetch_sop_sync_region_from_google_doc() or "").strip("\n")


def parse_region_to_schema(text: str) -> dict[str, list[dict[str, Any]]]:
    return parse_master_faq_schema(text or "")


def _dedupe_preserve(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item.strip())
    return out


def _merge_intent(local: dict[str, Any], google: dict[str, Any]) -> dict[str, Any]:
    g_aliases = [str(x).strip() for x in (google.get("aliases") or []) if str(x).strip()]
    l_aliases = [str(x).strip() for x in (local.get("aliases") or []) if str(x).strip()]
    merged_aliases = _dedupe_preserve(g_aliases + l_aliases)
    return {
        "intent_id": google.get("intent_id") or local.get("intent_id"),
        "aliases": merged_aliases,
        # Conflict rule: google answer wins.
        "answer": (google.get("answer") or local.get("answer") or "").strip(),
    }


def _merge_workflow(local: dict[str, Any], google: dict[str, Any]) -> dict[str, Any]:
    g_steps = [str(x).strip() for x in (google.get("steps") or []) if str(x).strip()]
    l_steps = [str(x).strip() for x in (local.get("steps") or []) if str(x).strip()]
    merged_steps = _dedupe_preserve(g_steps + l_steps)
    return {
        "workflow_id": google.get("workflow_id") or local.get("workflow_id"),
        "steps": merged_steps,
    }


def _merge_fields(local_fields: dict[str, Any], google_fields: dict[str, Any]) -> dict[str, str]:
    merged: dict[str, str] = {}
    for k, v in local_fields.items():
        merged[str(k)] = str(v).strip()
    for k, v in google_fields.items():
        # Conflict rule: google value wins.
        merged[str(k)] = str(v).strip()
    return merged


def _merge_data_like(local: dict[str, Any], google: dict[str, Any], *, key: str) -> dict[str, Any]:
    l_fields = local.get("fields") or {}
    g_fields = google.get("fields") or {}
    merged_fields = _merge_fields(l_fields, g_fields)
    return {key: google.get(key) or local.get(key), "fields": merged_fields}


def merge_schemas(local_schema: dict[str, list[dict[str, Any]]], google_schema: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    merged: dict[str, list[dict[str, Any]]] = {"intents": [], "workflows": [], "data": [], "dynamic": []}

    def _merge_kind(kind: str, key_name: str, merger: Any) -> None:
        by_key: dict[str, tuple[dict[str, Any] | None, dict[str, Any] | None]] = {}
        local_rows = local_schema.get(kind, []) or []
        google_rows = google_schema.get(kind, []) or []
        order: list[str] = []

        for row in google_rows:
            k = str(row.get(key_name) or "").strip()
            if not k:
                continue
            if k not in by_key:
                order.append(k)
            local_match = next((r for r in local_rows if str(r.get(key_name) or "").strip() == k), None)
            by_key[k] = (local_match, row)

        for row in local_rows:
            k = str(row.get(key_name) or "").strip()
            if not k:
                continue
            if k in by_key:
                continue
            order.append(k)
            by_key[k] = (row, None)

        out_rows: list[dict[str, Any]] = []
        for k in order:
            local_row, google_row = by_key[k]
            if local_row and google_row:
                out_rows.append(merger(local_row, google_row))
            elif google_row:
                out_rows.append(google_row)
            elif local_row:
                out_rows.append(local_row)
        merged[kind] = out_rows

    _merge_kind("intents", "intent_id", _merge_intent)
    _merge_kind("workflows", "workflow_id", _merge_workflow)
    _merge_kind("data", "name", lambda l, g: _merge_data_like(l, g, key="name"))
    _merge_kind("dynamic", "name", lambda l, g: _merge_data_like(l, g, key="name"))
    return merged


def render_merged_schema_to_markdown(merged_schema: dict[str, list[dict[str, Any]]]) -> str:
    return render_master_faq_schema(merged_schema, trailing_blank=True)


def _normalized_hash(obj: Any) -> str:
    blob = json.dumps(obj, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _state_now_iso() -> str:
    return datetime.now(tz=pytz.timezone(_tz_region())).isoformat()


def _load_state() -> dict[str, Any]:
    sp = _state_path()
    if not sp.exists():
        return {}
    try:
        return json.loads(sp.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(state: dict[str, Any]) -> None:
    sp = _state_path()
    sp.parent.mkdir(parents=True, exist_ok=True)
    sp.write_text(json.dumps(state, indent=2, ensure_ascii=True), encoding="utf-8")


def sync_sop_regions() -> dict[str, Any]:
    local_region = read_local_region()
    google_region = pull_google_region()
    if not google_region and not local_region:
        return {"ok": False, "error": "both_regions_empty"}

    local_schema = parse_region_to_schema(local_region)
    google_schema = parse_region_to_schema(google_region)
    merged_schema = merge_schemas(local_schema, google_schema)
    merged_region = render_merged_schema_to_markdown(merged_schema).strip("\n")

    path = _master_faq_path()
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    current = ensure_sop_sync_markers(current)
    updated = replace_sop_sync_region(current, merged_region)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(updated, encoding="utf-8")
    tmp.replace(path)

    writeback = push_master_faq_to_google_doc()
    writeback_ok = bool(writeback.get("ok")) or writeback.get("error") == "writeback_disabled"

    state = _load_state()
    state["last_sync_at"] = _state_now_iso()
    state["last_sync_date"] = datetime.now(tz=pytz.timezone(_tz_region())).strftime("%Y-%m-%d")
    state["hashes"] = {
        "local_before": _normalized_hash(local_schema),
        "google_before": _normalized_hash(google_schema),
        "merged": _normalized_hash(merged_schema),
    }
    state["counts"] = {k: len(v) for k, v in merged_schema.items()}
    state["writeback"] = writeback
    _save_state(state)

    return {
        "ok": writeback_ok,
        "local_updated": True,
        "google_writeback": writeback,
        "counts": state["counts"],
        "state_path": str(_state_path()),
    }
