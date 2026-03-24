from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import re

import requests

from config import (
    KAI_CHATWOOT_ACCOUNT_ID,
    KAI_CHATWOOT_API_BASE,
    KAI_CHATWOOT_API_TOKEN,
    KAI_CHATWOOT_RESOLUTION_TAG,
    MASTER_FAQ_PATH,
)
from session_state import list_faq_candidates, upsert_faq_candidate, update_faq_candidate_status
from support_runtime.sop_writeback import push_master_faq_to_google_doc


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_product(text: str) -> str:
    t = (text or "").lower()
    if "ka2" in t:
        return "KA2"
    if any(k in t for k in ("ka1", "ka1/1s", "1s")):
        return "KA1/1s"
    return "unknown"


def ingest_tagged_resolutions(limit: int = 50) -> dict[str, Any]:
    if not (KAI_CHATWOOT_API_BASE and KAI_CHATWOOT_API_TOKEN and KAI_CHATWOOT_ACCOUNT_ID):
        return {"ok": False, "error": "chatwoot_not_configured", "created": 0}
    headers = {"api_access_token": KAI_CHATWOOT_API_TOKEN}
    url = f"{KAI_CHATWOOT_API_BASE}/api/v1/accounts/{KAI_CHATWOOT_ACCOUNT_ID}/conversations"
    resp = requests.get(url, headers=headers, params={"status": "resolved", "page": 1}, timeout=20)
    resp.raise_for_status()
    payload = resp.json() if resp.content else {"data": []}
    created = 0
    for conv in (payload.get("data") or [])[:limit]:
        labels = conv.get("labels") or []
        if KAI_CHATWOOT_RESOLUTION_TAG not in labels:
            continue
        msgs = conv.get("messages") or []
        if not msgs:
            continue
        final = msgs[-1]
        final_text = (final.get("content") or "").strip()
        if not final_text:
            continue
        first_user = next((m for m in msgs if m.get("message_type") == 0), {})
        issue_summary = (first_user.get("content") or "").strip()[:400]
        if not issue_summary:
            issue_summary = "Post-escalation support resolution"
        source_message_id = str(final.get("id", ""))
        dedupe_key = f"cw:{conv.get('id')}:{source_message_id}"
        candidate = {
            "dedupe_key": dedupe_key,
            "issue_summary": issue_summary,
            "final_answer": final_text[:4000],
            "product": _extract_product(issue_summary + "\n" + final_text),
            "diagnostic_category": "diagnostic",
            "source_conversation_id": str(conv.get("id", "")),
            "source_message_id": source_message_id,
            "source_agent_id": str(final.get("sender_id", "")),
            "source_timestamp": final.get("created_at") or _iso_now(),
        }
        if upsert_faq_candidate(candidate):
            created += 1
    return {"ok": True, "created": created}


def publish_candidate_to_faq(candidate_id: int) -> dict[str, Any]:
    rows = [r for r in list_faq_candidates() if r["id"] == candidate_id]
    if not rows:
        return {"ok": False, "error": "candidate_not_found"}
    row = rows[0]
    if row["status"] not in {"approved", "published"}:
        return {"ok": False, "error": "candidate_not_approved"}
    faq_path = Path(MASTER_FAQ_PATH)
    faq_path.parent.mkdir(parents=True, exist_ok=True)
    existing = faq_path.read_text(encoding="utf-8") if faq_path.exists() else ""
    prov_key = f"conv={row['source_conversation_id']} msg={row['source_message_id']}"
    if prov_key in existing:
        return {"ok": True, "published_id": candidate_id, "skipped": "already_published", "google_docs_writeback": {"ok": True, "skipped": True}}
    alias = re.sub(r"\s+", " ", row["issue_summary"]).strip()
    generated_id = re.sub(r"[^a-z0-9]+", "_", alias.lower()).strip("_")[:80] or f"candidate_{row['id']}"
    block = (
        f"\n\n## intent: {generated_id}\n"
        "aliases:\n"
        f"- {alias}\n"
        "answer:\n"
        f"{row['final_answer']}\n\n"
        f"<!-- provenance: conv={row['source_conversation_id']} msg={row['source_message_id']} "
        f"agent={row['source_agent_id']} product={row['product']} -->\n"
    )
    with faq_path.open("a", encoding="utf-8") as f:
        f.write(block)
    update_faq_candidate_status(candidate_id, "published")
    writeback = push_master_faq_to_google_doc()
    return {"ok": True, "published_id": candidate_id, "google_docs_writeback": writeback}
