#!/usr/bin/env python3
"""Clear Shadou session + memory for a WhatsApp phone number.

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
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shadou.lib.phone_identity import (  # noqa: E402
    canonical_my_mobile,
    candidate_user_ids,
    digits_only,
)
from shadou.lib.session_state import (  # noqa: E402
    DB_PATH,
    get_all_user_ids,
    get_session,
    init_db,
    reset_memory,
)


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
