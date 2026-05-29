"""Append a Studio agent reply to tenant sessions.db."""
from __future__ import annotations

import json
import os
import sys


def main() -> int:
    if len(sys.argv) != 4:
        print(json.dumps({"ok": False, "error": "usage: kai_reply.py KAI_HOME user_id text"}))
        return 1

    kai_home, user_id, text = sys.argv[1], sys.argv[2], sys.argv[3]
    text = (text or "").strip()
    if not user_id or not text:
        print(json.dumps({"ok": False, "error": "missing_user_or_text"}))
        return 1

    os.environ["KAI_HOME"] = kai_home

    from kai.lib.session_state import add_message_to_history, update_session_summary

    add_message_to_history(user_id, "agent", text)
    update_session_summary(user_id, "agent", text)

    print(json.dumps({"ok": True}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
