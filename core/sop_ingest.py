"""Build SOP Q&A list from master_faq.md plus optional Google Doc sync."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from config import MASTER_FAQ_PATH, RAG_DIR, SOP_DOC_URL, SOP_JSON_PATH
from core.faq_markdown import (
    ensure_sop_sync_markers,
    parse_faq_markdown,
    replace_sop_sync_region,
    render_qas_markdown,
)
from sop_doc_loader import fetch_sop_doc_text, parse_qas_from_text

log = logging.getLogger("kai.sop_ingest")


def ingest_sop_qas() -> list[dict]:
    """
    1. Optionally fetch Google Doc and rewrite sop-sync region in master_faq.md.
    2. Parse full master_faq.md into Q/A list (all ## sections).
    3. Fallback to doc-only QAs or legacy sop_data.json if markdown empty.
    """
    path = Path(MASTER_FAQ_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.is_file():
        text = path.read_text(encoding="utf-8")
    else:
        text = "# Kommu FAQ\n\n" + ensure_sop_sync_markers("")

    doc_qas: list[dict] = []
    if SOP_DOC_URL:
        try:
            raw = fetch_sop_doc_text()
            if raw:
                doc_qas = parse_qas_from_text(raw) or []
        except Exception as exc:  # noqa: BLE001
            log.warning("SOP doc fetch failed: %s", exc)

    if doc_qas:
        text = ensure_sop_sync_markers(text)
        text = replace_sop_sync_region(text, render_qas_markdown(doc_qas))
        path.write_text(text, encoding="utf-8")
        log.info("Updated sop-sync region in %s (%s QAs from doc)", path, len(doc_qas))

    qas = parse_faq_markdown(path.read_text(encoding="utf-8")) if path.is_file() else []

    if not qas and doc_qas:
        qas = doc_qas
        log.info("Using doc-only QAs (no markdown sections): %s items", len(qas))

    if not qas:
        try:
            with open(SOP_JSON_PATH, encoding="utf-8") as f:
                legacy = json.load(f)
            if isinstance(legacy, list):
                qas = [x for x in legacy if isinstance(x, dict) and x.get("question") and x.get("answer")]
                log.info("Fallback to sop_data.json: %s items", len(qas))
        except Exception:
            pass

    if qas:
        Path(RAG_DIR).mkdir(parents=True, exist_ok=True)
        with open(SOP_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(qas, f, ensure_ascii=False, indent=2)

    return qas
