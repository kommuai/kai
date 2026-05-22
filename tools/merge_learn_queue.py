#!/usr/bin/env python3
"""Admin CLI: list / merge / reject FAQ learn-queue proposals."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import MASTER_FAQ_PATH, resolve_master_faq_path
from kai.support_runtime.compiler import compile_canonical_knowledge
from kai.support_runtime.faq_learn_queue import list_proposals, load_proposal, set_proposal_status
from kai.support_runtime.faq_merge import merge_proposal_into_master


def main() -> int:
    parser = argparse.ArgumentParser(description="FAQ learn queue merge tool")
    parser.add_argument("--list", action="store_true", help="List pending proposals")
    parser.add_argument("--show", metavar="ID", help="Show one proposal")
    parser.add_argument("--apply", metavar="ID", help="Merge proposal.json into master_faq.md")
    parser.add_argument("--reject", metavar="ID", help="Mark proposal rejected")
    parser.add_argument("--compile", action="store_true", help="Run compile_canonical_knowledge after apply")
    parser.add_argument("--master", default="", help="Override master FAQ path")
    args = parser.parse_args()

    master = Path(args.master or resolve_master_faq_path() or MASTER_FAQ_PATH)

    if args.list:
        rows = list_proposals(status="pending")
        if not rows:
            print("No pending proposals.")
            return 0
        for row in rows:
            print(
                f"{row.get('proposal_id')}\t{row.get('trigger')}\t"
                f"{row.get('created_at')}\t{row.get('summary', row.get('has_structured', ''))}"
            )
        return 0

    if args.show:
        print(json.dumps(load_proposal(args.show), indent=2, ensure_ascii=False))
        return 0

    if args.apply:
        out = merge_proposal_into_master(args.apply, master)
        print(json.dumps(out, indent=2))
        if not out.get("ok"):
            return 1
        if args.compile:
            counts = compile_canonical_knowledge()
            print("compiled:", counts)
        return 0

    if args.reject:
        set_proposal_status(args.reject, "rejected", note="cli reject")
        print(f"rejected {args.reject}")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
