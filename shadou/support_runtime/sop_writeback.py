from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import re
from typing import Any

from shadou.settings import get_settings

SOP_SYNC_START = "<!-- sop-sync:start -->"
SOP_SYNC_END = "<!-- sop-sync:end -->"


def _is_enabled() -> bool:
    return bool(get_settings().shadou_sop_writeback_enabled)


def _load_service_account_info() -> dict[str, Any]:
    raw = (get_settings().google_sheets_credentials_json or "").strip()
    if not raw:
        return {}
    if raw.startswith("{"):
        return json.loads(raw)
    if os.path.isfile(raw):
        with open(raw, "r", encoding="utf-8") as fh:
            return json.load(fh)
    try:
        decoded = base64.b64decode(raw).decode("utf-8")
        return json.loads(decoded)
    except Exception:  # noqa: BLE001
        return {}


def _extract_sync_region(full_text: str) -> str:
    if SOP_SYNC_START not in full_text or SOP_SYNC_END not in full_text:
        raise ValueError("missing_sop_sync_markers_in_master_faq")
    start = full_text.index(SOP_SYNC_START) + len(SOP_SYNC_START)
    end = full_text.index(SOP_SYNC_END, start)
    return full_text[start:end].strip("\n")


def _format_for_google_doc(sync_text: str) -> str:
    # Keep sync text plain; bold styling is applied via Docs API text styles.
    return sync_text


def _flatten_doc_text_segments(doc: dict[str, Any]) -> tuple[str, list[tuple[int, int, str]]]:
    parts: list[str] = []
    segments: list[tuple[int, int, str]] = []
    for block in doc.get("body", {}).get("content", []):
        para = block.get("paragraph") or {}
        for el in para.get("elements", []):
            tr = (el.get("textRun") or {}).get("content")
            if not tr:
                continue
            s = int(el.get("startIndex", 0))
            e = int(el.get("endIndex", s + len(tr)))
            segments.append((s, e, tr))
            parts.append(tr)
    return "".join(parts), segments


def _doc_index_for_offset(segments: list[tuple[int, int, str]], target_offset: int) -> int:
    seen = 0
    for s, e, txt in segments:
        seg_len = len(txt)
        if target_offset <= seen + seg_len:
            return s + (target_offset - seen)
        seen += seg_len
    if segments:
        return segments[-1][1]
    return 1


def push_master_faq_to_google_doc() -> dict[str, Any]:
    if not _is_enabled():
        return {"ok": False, "error": "writeback_disabled"}
    doc_id = (get_settings().google_docs_sop_doc_id or "").strip()
    if not doc_id:
        return {"ok": False, "error": "missing_google_docs_doc_id"}
    faq_path = get_settings().resolve_master_faq_path()
    if not faq_path.exists():
        return {"ok": False, "error": "master_faq_not_found"}
    text = faq_path.read_text(encoding="utf-8")
    if not text.strip():
        return {"ok": False, "error": "master_faq_empty"}
    try:
        sync_payload = _extract_sync_region(text)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"google_libs_missing:{exc}"}

    info = _load_service_account_info()
    if not info:
        return {"ok": False, "error": "missing_or_invalid_service_account_credentials"}

    try:
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/documents", "https://www.googleapis.com/auth/drive"]
        )
        docs = build("docs", "v1", credentials=creds, cache_discovery=False)
        doc = docs.documents().get(documentId=doc_id).execute()
        doc_text, segments = _flatten_doc_text_segments(doc)
        if SOP_SYNC_START not in doc_text or SOP_SYNC_END not in doc_text:
            return {"ok": False, "error": "missing_sop_sync_markers_in_google_doc"}
        start_off = doc_text.index(SOP_SYNC_START) + len(SOP_SYNC_START)
        end_off = doc_text.index(SOP_SYNC_END, start_off)
        start_idx = _doc_index_for_offset(segments, start_off)
        end_idx = _doc_index_for_offset(segments, end_off)

        replacement = "\n" + _format_for_google_doc(sync_payload.strip()) + "\n"
        requests = [{"deleteContentRange": {"range": {"startIndex": start_idx, "endIndex": end_idx}}}]
        requests.append({"insertText": {"location": {"index": start_idx}, "text": replacement}})
        # Apply native bold style to intent header lines in inserted region.
        cursor = 0
        for line in replacement.splitlines(keepends=True):
            bare = line.rstrip("\n")
            if re.match(r"^##\s+intent:\s+[A-Za-z0-9_\-./]+\s*$", bare):
                line_start = start_idx + cursor
                line_end = line_start + len(bare)
                requests.append(
                    {
                        "updateTextStyle": {
                            "range": {"startIndex": line_start, "endIndex": line_end},
                            "textStyle": {"bold": True},
                            "fields": "bold",
                        }
                    }
                )
            cursor += len(line)

        docs.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()
        return {"ok": True, "doc_id": doc_id, "mode": "sync_region_only"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"google_docs_write_failed:{exc}"}
