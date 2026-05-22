#!/usr/bin/env python3
"""Clear Kai session + memory for a WhatsApp phone number.

Examples:
  python tools/clear_chat.py 0173611088
  python tools/clear_chat.py +60173611088
  python tools/clear_chat.py 0173611088 --dry-run

Uses the same SQLite DB as production (`SESSION_DB_PATH` / `data/sessions.db`).
In Docker, run against the mounted DB:
  docker exec kommu_chatbot python tools/clear_chat.py 0173611088
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kai.lib.session_state import (  # noqa: E402
    DB_PATH,
    get_all_user_ids,
    get_session,
    init_db,
    reset_memory,
)


def _digits_only(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def canonical_my_mobile(raw: str) -> str:
    """Normalize Malaysian mobile to +60XXXXXXXXX for matching."""
    d = _digits_only(raw)
    if not d:
        return ""
    if d.startswith("60"):
        return f"+{d}"
    if d.startswith("0"):
        return f"+60{d[1:]}"
    return f"+{d}"


def candidate_user_ids(raw: str) -> list[str]:
    """Possible session keys stored by n8n / Chatwoot."""
    raw = (raw or "").strip()
    canon = canonical_my_mobile(raw)
    d = _digits_only(raw)
    out: list[str] = []
    for item in (raw, canon, f"0{canon[3:]}" if canon.startswith("+60") else "", d, f"+{d}"):
        item = (item or "").strip()
        if item and item not in out:
            out.append(item)
    return out


def find_matching_user_ids(phone_input: str) -> list[str]:
    init_db()
    target = canonical_my_mobile(phone_input)
    if not target:
        return []

    matches: list[str] = []
    seen: set[str] = set()

    for uid in get_all_user_ids():
        if canonical_my_mobile(uid) == target and uid not in seen:
            matches.append(uid)
            seen.add(uid)

    for cid in candidate_user_ids(phone_input):
        if cid in get_all_user_ids() and cid not in seen:
            matches.append(cid)
            seen.add(cid)

    return matches


def main() -> int:
    parser = argparse.ArgumentParser(description="Clear chat history for a phone number.")
    parser.add_argument("phone", help="e.g. 0173611088 or +60173611088")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be cleared without writing",
    )
    args = parser.parse_args()

    print(f"Database: {DB_PATH}")
    matches = find_matching_user_ids(args.phone)
    if not matches:
        print(f"No session found for {args.phone!r} (canonical {canonical_my_mobile(args.phone)!r}).")
        print("Known user_ids:")
        for uid in get_all_user_ids():
            print(f"  - {uid}")
        return 1

    for uid in matches:
        session = get_session(uid)
        history_len = len(session.get("history") or [])
        summary = (session.get("session_summary") or "")[:80]
        print(f"Match: {uid!r} (history turns: {history_len}, summary: {summary!r}...)")
        if args.dry_run:
            continue
        reset_memory(uid)
        print(f"Cleared: {uid!r}")

    if args.dry_run:
        print("Dry run — no changes written.")
    else:
        print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
