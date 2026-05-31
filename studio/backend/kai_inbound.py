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
        print(json.dumps({"ok": False, "error": "usage: kai_inbound.py KAI_HOME user_id text [payload_json]"}))
        return 1

    kai_home, user_id, text = sys.argv[1], sys.argv[2], sys.argv[3]
    text = (text or "").strip()
    user_id = (user_id or "").strip()
    if not user_id:
        print(json.dumps({"ok": False, "error": "missing_user_id"}))
        return 1

    os.environ["KAI_HOME"] = kai_home

    from kai.lib.lang import resolve_lang
    from kai.lib.session_state import init_db
    from kai.support_runtime.gateway import run_support_turn

    init_db()

    payload: dict = {}
    if len(sys.argv) >= 5 and sys.argv[4].strip():
        try:
            raw = json.loads(sys.argv[4])
            if isinstance(raw, dict):
                payload = raw
        except json.JSONDecodeError:
            pass

    meta = payload.get("contact") if isinstance(payload.get("contact"), dict) else {}
    if meta:
        _persist_contact_meta(user_id, meta)

    media = payload.get("media") if isinstance(payload.get("media"), dict) else None
    media_meta: dict = {}

    lang = resolve_lang(user_id=user_id)

    if media:
        from kai.media.enrich import enrich_inbound_media

        try:
            enriched = enrich_inbound_media(media, lang=lang)
            media_meta = enriched.metadata or {}
            if enriched.skipped_runtime:
                print(
                    json.dumps(
                        {
                            "ok": True,
                            "answer": enriched.text,
                            "decision": enriched.decision or "media_guard",
                            "skipped_runtime": True,
                            "media": {
                                "modality": enriched.modality,
                                "confidence": enriched.confidence,
                                "stored_path": enriched.stored_path,
                            },
                        }
                    )
                )
                return 0
            text = enriched.text
        except Exception as exc:
            from kai.content.channels import get_channel_config

            ch = get_channel_config()
            answer = ch.media_guard_en if lang == "EN" else ch.media_guard_bm
            print(
                json.dumps(
                    {
                        "ok": True,
                        "answer": answer,
                        "decision": "media_enrich_failed",
                        "skipped_runtime": True,
                        "error": str(exc)[:200],
                    }
                )
            )
            return 0

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

    result = outcome.to_inbound_json()
    if media_meta:
        result["media"] = media_meta
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
