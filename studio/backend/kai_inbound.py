"""Process an inbound WhatsApp (or Studio) user message through the Kai support runtime."""
from __future__ import annotations

import json
import os
import sys


def _persist_contact_meta(user_id: str, meta: dict) -> None:
    from store_contact_meta import persist_contact_meta

    persist_contact_meta(user_id, meta)


def main() -> int:
    if len(sys.argv) < 4:
        print(json.dumps({"ok": False, "error": "usage: kai_inbound.py KAI_HOME user_id text [contact_json]"}))
        return 1

    kai_home, user_id, text = sys.argv[1], sys.argv[2], sys.argv[3]
    text = (text or "").strip()
    user_id = (user_id or "").strip()
    if not user_id:
        print(json.dumps({"ok": False, "error": "missing_user_id"}))
        return 1

    os.environ["KAI_HOME"] = kai_home

    from kai.lib.lang_detect import is_malay
    from kai.lib.session_state import init_db
    from kai.support_runtime.gateway import run_support_turn

    init_db()

    if len(sys.argv) >= 5 and sys.argv[4].strip():
        try:
            meta = json.loads(sys.argv[4])
            if isinstance(meta, dict):
                _persist_contact_meta(user_id, meta)
        except json.JSONDecodeError:
            pass

    lang = "BM" if is_malay(text) else "EN"

    if not text:
        from kai.content.channels import get_channel_config

        ch = get_channel_config()
        answer = ch.media_guard_en if lang == "EN" else ch.media_guard_bm
        print(json.dumps({"ok": True, "answer": answer, "decision": "media_guard", "skipped_runtime": True}))
        return 0

    try:
        outcome = run_support_turn(
            user_id=user_id,
            text=text,
            lang=lang,
            use_pre_router=True,
            apply_grounding=True,
        )
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)[:500]}))
        return 1

    print(json.dumps(outcome.to_inbound_json()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
