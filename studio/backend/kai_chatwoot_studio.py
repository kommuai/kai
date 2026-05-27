"""Kai Studio → Chatwoot actions (stdin JSON, argv[1] = KAI_HOME)."""
from __future__ import annotations

import json
import os
import sys


def out(obj: object) -> None:
    print(json.dumps(obj))
    sys.stdout.flush()


def main() -> int:
    if len(sys.argv) != 2:
        out({"ok": False, "error": "usage: kai_chatwoot_studio.py KAI_HOME <stdin json>"})
        return 1

    os.environ["KAI_HOME"] = sys.argv[1]
    try:
        req = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError as exc:
        out({"ok": False, "error": f"invalid_json:{exc}"})
        return 1

    action = str(req.get("action") or "").strip()
    from kai.integrations.chatwoot.client import ChatwootClient
    from kai.lib.session_state import freeze, get_session

    client = ChatwootClient()

    if action == "ping":
        out({"ok": True, "configured": client.is_configured()})
        return 0

    if action == "account_labels":
        if not client.is_configured():
            out({"ok": True, "items": []})
            return 0
        items, err = client.list_account_labels()
        if err and not items:
            out({"ok": False, "error": err})
            return 1
        out({"ok": True, "items": items})
        return 0

    uid = str(req.get("user_id") or "").strip()
    if not uid:
        out({"ok": False, "error": "missing_user_id"})
        return 1

    sess = get_session(uid)
    cw = str(sess.get("chatwoot_conversation_id") or "").strip()

    if action == "get_meta":
        if not client.is_configured():
            out(
                {
                    "ok": True,
                    "configured": False,
                    "conversation_id": cw or None,
                    "status": None,
                    "labels": [],
                }
            )
            return 0
        if not cw:
            out(
                {
                    "ok": True,
                    "configured": True,
                    "conversation_id": None,
                    "status": None,
                    "labels": [],
                }
            )
            return 0
        conv, err = client.get_conversation(cw)
        if conv is None:
            out({"ok": False, "error": err})
            return 1
        status = str(conv.get("status") or "")
        labels, _lerr = client.get_conversation_labels(cw)
        out(
            {
                "ok": True,
                "configured": True,
                "conversation_id": cw,
                "status": status or None,
                "labels": labels,
            }
        )
        return 0

    if not client.is_configured():
        out({"ok": False, "error": "chatwoot_not_configured"})
        return 1
    if not cw:
        out({"ok": False, "error": "no_chatwoot_conversation_id"})
        return 1

    if action == "set_status":
        status = str(req.get("status") or "").strip().lower()
        snooze = req.get("snoozed_until")
        sn_int = int(snooze) if snooze is not None and str(snooze).strip() != "" else None
        ok, err = client.set_conversation_status(cw, status, snoozed_until=sn_int)
        if not ok:
            out({"ok": False, "error": err})
            return 1
        if status == "resolved":
            freeze(uid, False)
        out({"ok": True})
        return 0

    if action == "private_note":
        text = str(req.get("text") or "").strip()
        if not text:
            out({"ok": False, "error": "empty_text"})
            return 1
        ok, err = client.create_private_note(cw, text)
        if not ok:
            out({"ok": False, "error": err})
            return 1
        out({"ok": True})
        return 0

    if action == "set_labels":
        labels = req.get("labels")
        if not isinstance(labels, list):
            out({"ok": False, "error": "labels_must_be_array"})
            return 1
        lab_strs = [str(x).strip() for x in labels if str(x).strip()]
        ok, err = client.set_conversation_labels(cw, lab_strs)
        if not ok:
            out({"ok": False, "error": err})
            return 1
        out({"ok": True, "labels": lab_strs})
        return 0

    if action == "human_handover":
        ok, err = client.toggle_handover(cw)
        if not ok:
            out({"ok": False, "error": err})
            return 1
        freeze(uid, True)
        out({"ok": True})
        return 0

    if action == "resume_bot":
        freeze(uid, False)
        out({"ok": True})
        return 0

    out({"ok": False, "error": f"unknown_action:{action}"})
    return 1


if __name__ == "__main__":
    sys.exit(main())
