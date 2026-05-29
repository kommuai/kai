"""Persist WhatsApp contact handle / phone into tenant sessions.db memory_facts."""
from __future__ import annotations

import json
import os
import sys


def persist_contact_meta(user_id: str, meta: dict) -> None:
    from kai.lib.session_state import init_db, upsert_memory_fact

    init_db()
    push = (meta.get("pushName") or meta.get("push_name") or meta.get("notify") or "").strip()
    verified = (meta.get("verifiedName") or meta.get("verifiedBizName") or "").strip()
    phone = (meta.get("phone") or "").strip()

    handle = push or verified
    if handle:
        upsert_memory_fact(
            user_id,
            "identity",
            "wa_push_name",
            handle[:120],
            source="whatsapp",
            ttl_days=365,
        )
    if phone and phone != user_id:
        upsert_memory_fact(
            user_id,
            "device_account",
            "wa_phone",
            phone[:32],
            source="whatsapp",
            ttl_days=365,
        )


def main() -> int:
    if len(sys.argv) < 4:
        print(json.dumps({"ok": False, "error": "usage: store_contact_meta.py KAI_HOME user_id JSON"}))
        return 1
    os.environ["KAI_HOME"] = sys.argv[1]
    user_id = (sys.argv[2] or "").strip()
    if not user_id:
        return 1
    try:
        meta = json.loads(sys.argv[3])
    except json.JSONDecodeError:
        return 1
    if not isinstance(meta, dict):
        return 1
    persist_contact_meta(user_id, meta)
    print(json.dumps({"ok": True}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
