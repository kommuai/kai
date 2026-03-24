#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from session_state import list_faq_candidates, update_faq_candidate_status  # noqa: E402
from support_runtime.faq_feedback import ingest_tagged_resolutions, publish_candidate_to_faq  # noqa: E402


def _print(data: dict | list) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=True))


def _api_request(method: str, base_url: str, path: str) -> dict:
    url = f"{base_url.rstrip('/')}{path}"
    resp = requests.request(method=method, url=url, timeout=20)
    resp.raise_for_status()
    return resp.json() if resp.content else {"ok": True}


def cmd_poll(args: argparse.Namespace) -> None:
    if args.mode == "api":
        out = _api_request("POST", args.base_url, "/admin/faq-feedback/poll")
    else:
        out = ingest_tagged_resolutions()
    _print(out)


def cmd_list(args: argparse.Namespace) -> None:
    if args.mode == "api":
        suffix = f"?status={args.status}" if args.status else ""
        out = _api_request("GET", args.base_url, f"/admin/faq-candidates{suffix}")
    else:
        out = {"ok": True, "items": list_faq_candidates(status=args.status)}
    _print(out)


def cmd_approve(args: argparse.Namespace) -> None:
    if args.mode == "api":
        out = _api_request("POST", args.base_url, f"/admin/faq-candidates/{args.id}/approve")
    else:
        out = {"ok": update_faq_candidate_status(args.id, "approved")}
    _print(out)


def cmd_reject(args: argparse.Namespace) -> None:
    if args.mode == "api":
        out = _api_request("POST", args.base_url, f"/admin/faq-candidates/{args.id}/reject")
    else:
        out = {"ok": update_faq_candidate_status(args.id, "rejected")}
    _print(out)


def cmd_publish(args: argparse.Namespace) -> None:
    if args.mode == "api":
        out = _api_request("POST", args.base_url, f"/admin/faq-candidates/{args.id}/publish")
    else:
        out = publish_candidate_to_faq(args.id)
    _print(out)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FAQ approval CLI for Kai")
    parser.add_argument("--mode", choices=["api", "local"], default="api", help="Use API endpoints or local DB calls")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Admin API base URL for --mode api")
    sub = parser.add_subparsers(dest="command", required=True)

    poll = sub.add_parser("poll", help="Pull tagged resolutions into FAQ candidate queue")
    poll.set_defaults(func=cmd_poll)

    ls = sub.add_parser("list", help="List FAQ candidates")
    ls.add_argument("--status", choices=["pending_review", "approved", "rejected", "published"], default=None)
    ls.set_defaults(func=cmd_list)

    ap = sub.add_parser("approve", help="Approve candidate by id")
    ap.add_argument("id", type=int)
    ap.set_defaults(func=cmd_approve)

    rj = sub.add_parser("reject", help="Reject candidate by id")
    rj.add_argument("id", type=int)
    rj.set_defaults(func=cmd_reject)

    pub = sub.add_parser("publish", help="Publish candidate by id")
    pub.add_argument("id", type=int)
    pub.set_defaults(func=cmd_publish)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
