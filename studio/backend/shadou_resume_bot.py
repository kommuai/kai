"""Resume AI support for a handover (frozen) conversation in tenant sessions.db."""
from __future__ import annotations

import json
import os
import sys


def main() -> int:
    if len(sys.argv) != 3:
        print(json.dumps({"ok": False, "error": "usage: shadou_resume_bot.py SHADOU_HOME user_id"}))
        return 1

    shadou_home, user_id = sys.argv[1], sys.argv[2]
    user_id = (user_id or "").strip()
    if not user_id:
        print(json.dumps({"ok": False, "error": "missing_user_id"}))
        return 1

    os.environ["SHADOU_HOME"] = shadou_home

    from shadou.content.copy import get_chat_copy
    from shadou.lib.session_state import (
        add_message_to_history,
        freeze,
        get_session,
        init_db,
        save_session,
        update_session_summary,
    )

    init_db()
    sess = get_session(user_id)
    if not sess.get("frozen"):
        print(json.dumps({"ok": True, "user_id": user_id, "frozen": False, "already_active": True}))
        return 0

    lang = (sess.get("lang") or "EN").upper()
    freeze(user_id, False)
    sess = get_session(user_id)
    if sess.get("handover"):
        sess.pop("handover", None)
        save_session(user_id, sess)

    cp = get_chat_copy()
    msg = cp.resume_bm if lang == "BM" else cp.resume_en
    add_message_to_history(user_id, "assistant", msg)
    update_session_summary(user_id, "assistant", msg)

    print(
        json.dumps(
            {
                "ok": True,
                "user_id": user_id,
                "frozen": False,
                "message": msg,
                "already_active": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
