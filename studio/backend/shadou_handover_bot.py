"""Force human handover (freeze session) for a Studio inbox conversation."""
from __future__ import annotations

import json
import os
import sys


def main() -> int:
    if len(sys.argv) != 3:
        print(json.dumps({"ok": False, "error": "usage: shadou_handover_bot.py SHADOU_HOME user_id"}))
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
        update_session_summary,
    )
    from shadou.services.container import shadou_service

    init_db()
    sess = get_session(user_id)
    if sess.get("frozen"):
        print(
            json.dumps(
                {
                    "ok": True,
                    "user_id": user_id,
                    "frozen": True,
                    "already_in_handover": True,
                    "message": None,
                }
            )
        )
        return 0

    lang = (sess.get("lang") or "EN").upper()
    freeze(user_id, True)

    cp = get_chat_copy()
    msg = cp.handover_live_agent_en if lang == "EN" else cp.handover_live_agent_bm
    if not shadou_service.is_office_hours():
        msg += cp.after_hours_suffix(lang)
    msg = shadou_service.finalize_reply(user_id, msg, lang, suppress=True)
    add_message_to_history(user_id, "assistant", msg)
    update_session_summary(user_id, "assistant", msg)

    print(
        json.dumps(
            {
                "ok": True,
                "user_id": user_id,
                "frozen": True,
                "message": msg,
                "already_in_handover": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
