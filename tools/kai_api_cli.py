#!/usr/bin/env python3
"""CLI to exercise Kai HTTP APIs (message, query, search, admin).

Examples:
  # Single message (WhatsApp/n8n shape)
  python3 tools/kai_api_cli.py message "What cars are supported?"
  python3 tools/kai_api_cli.py message "Corolla Cross install" --phone +60123456789

  # Multi-turn REPL (same session / phone_number)
  python3 tools/kai_api_cli.py chat --phone test-cli-user

  # Machine-agent endpoints (needs x-api-key)
  python3 tools/kai_api_cli.py query "What is KommuAssist?"
  python3 tools/kai_api_cli.py search "installation appointment"

  # Admin (set ADMIN_TOKEN in env)
  python3 tools/kai_api_cli.py admin refresh-sop
  python3 tools/kai_api_cli.py admin reset-memory --phone +60123456789

Env:
  KAI_API_BASE_URL   default http://127.0.0.1:6090
  KAI_API_KEY        default internal-key (for /v2/agent/query|search)
  ADMIN_TOKEN        required for admin/* subcommands
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import requests

DEFAULT_BASE = os.getenv("KAI_API_BASE_URL", "http://127.0.0.1:6090").rstrip("/")
DEFAULT_API_KEY = os.getenv("KAI_API_KEY", "internal-key")
DEFAULT_PHONE = os.getenv("KAI_API_PHONE", "cli-test-user")


def _pretty(data: Any, *, raw: bool) -> str:
    if raw:
        return json.dumps(data, indent=2, ensure_ascii=False)
    if isinstance(data, dict):
        msg = data.get("message")
        if isinstance(msg, str) and msg.strip():
            lines = [msg.strip()]
            for key in ("type", "next_state", "decision", "capability_used", "confidence"):
                if key in data and data[key] is not None:
                    lines.append(f"  [{key}] {data[key]}")
            if data.get("source_ids"):
                lines.append(f"  [source_ids] {data['source_ids']}")
            if data.get("trace_id"):
                lines.append(f"  [trace_id] {data['trace_id']}")
            if data.get("latency_ms") is not None:
                lines.append(f"  [latency_ms] {data['latency_ms']}")
            return "\n".join(lines)
        if "answer" in data:
            lines = [str(data.get("answer") or "").strip()]
            if data.get("capability_used"):
                lines.append(f"  [capability_used] {data['capability_used']}")
            if data.get("trace_id"):
                lines.append(f"  [trace_id] {data['trace_id']}")
            return "\n".join(lines) if lines[0] else json.dumps(data, indent=2, ensure_ascii=False)
    return json.dumps(data, indent=2, ensure_ascii=False)


def _request(
    method: str,
    path: str,
    *,
    base: str,
    json_body: dict | None = None,
    headers: dict | None = None,
    params: dict | None = None,
    timeout: float = 120.0,
) -> tuple[int, Any]:
    url = f"{base}{path}"
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    resp = requests.request(method, url, json=json_body, headers=h, params=params, timeout=timeout)
    try:
        body = resp.json()
    except Exception:
        body = {"_raw": resp.text}
    return resp.status_code, body


def cmd_message(args: argparse.Namespace) -> int:
    payload: dict[str, Any] = {
        "phone_number": args.phone,
        "content": args.text,
    }
    if args.debug:
        payload["debug_route_agent"] = True
    path = "/v2/agent/message" if args.v2 else "/agent/message"
    code, body = _request("POST", path, base=args.base, json_body=payload)
    print(_pretty(body, raw=args.json))
    if code >= 400:
        print(f"HTTP {code}", file=sys.stderr)
        return 1
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    payload = {"user_id": args.user_id, "query": args.text, "lang": args.lang}
    code, body = _request(
        "POST",
        "/v2/agent/query",
        base=args.base,
        json_body=payload,
        headers={"x-api-key": args.api_key},
    )
    print(_pretty(body, raw=args.json))
    if code >= 400:
        print(f"HTTP {code}", file=sys.stderr)
        return 1
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    payload = {"user_id": args.user_id, "query": args.text, "lang": args.lang}
    code, body = _request(
        "POST",
        "/v2/agent/search",
        base=args.base,
        json_body=payload,
        headers={"x-api-key": args.api_key},
    )
    print(_pretty(body, raw=args.json))
    if code >= 400:
        print(f"HTTP {code}", file=sys.stderr)
        return 1
    return 0


def cmd_chat(args: argparse.Namespace) -> int:
    print(f"Kai API chat — phone={args.phone} base={args.base}")
    print("Commands: /quit, /reset (admin reset-memory), /json toggle")
    print("-" * 40)
    show_json = args.json
    while True:
        try:
            line = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line in {"/quit", "/exit", "/q"}:
            break
        if line == "/json":
            show_json = not show_json
            print(f"json output: {show_json}")
            continue
        if line == "/reset":
            token = os.getenv("ADMIN_TOKEN", "").strip()
            if not token:
                print("Set ADMIN_TOKEN to use /reset", file=sys.stderr)
                continue
            code, body = _request(
                "POST",
                "/admin/reset_memory",
                base=args.base,
                params={"user_id": args.phone},
                headers={"x-admin-token": token},
            )
            print(body if isinstance(body, str) else _pretty(body, raw=True))
            print(f"reset HTTP {code}")
            continue

        ns = argparse.Namespace(
            base=args.base,
            phone=args.phone,
            text=line,
            debug=args.debug,
            v2=True,
            json=show_json,
        )
        if cmd_message(ns) != 0:
            print("(request failed — is the server up?)", file=sys.stderr)
    return 0


def cmd_admin(args: argparse.Namespace) -> int:
    token = os.getenv("ADMIN_TOKEN", "").strip()
    if not token:
        print("ADMIN_TOKEN is not set", file=sys.stderr)
        return 1
    headers = {"x-admin-token": token}
    if args.admin_cmd == "refresh-sop":
        code, body = _request("POST", "/admin/refresh-sop", base=args.base, headers=headers)
    elif args.admin_cmd == "reset-memory":
        code, body = _request(
            "POST",
            "/admin/reset_memory",
            base=args.base,
            headers=headers,
            params={"user_id": args.phone},
        )
    elif args.admin_cmd == "tech-backlog-tabs":
        code, body = _request("GET", "/admin/tech-backlog/tabs", base=args.base, headers=headers)
    else:
        print(f"unknown admin command: {args.admin_cmd}", file=sys.stderr)
        return 1
    print(_pretty(body, raw=args.json))
    if code >= 400:
        print(f"HTTP {code}", file=sys.stderr)
        return 1
    return 0


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--base", default=DEFAULT_BASE, help=f"API base URL (default {DEFAULT_BASE})")
    p.add_argument("--json", action="store_true", help="Print full JSON response")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Kai HTTP API test CLI")
    sub = ap.add_subparsers(dest="command", required=True)

    p_msg = sub.add_parser("message", help="POST /v2/agent/message (default chat route)")
    _add_common(p_msg)
    p_msg.add_argument("text", help="User message content")
    p_msg.add_argument("--phone", default=DEFAULT_PHONE, help="phone_number / session id")
    p_msg.add_argument("--debug", action="store_true", help="Set debug_route_agent=true")
    p_msg.add_argument("--legacy-path", action="store_true", help="Use POST /agent/message instead of /v2")
    p_msg.set_defaults(func=cmd_message, v2=True)

    def _legacy_flag(ns: argparse.Namespace) -> int:
        ns.v2 = not ns.legacy_path
        return cmd_message(ns)

    p_msg.set_defaults(func=_legacy_flag)

    p_chat = sub.add_parser("chat", help="Interactive multi-turn session")
    _add_common(p_chat)
    p_chat.add_argument("--phone", default=DEFAULT_PHONE)
    p_chat.add_argument("--debug", action="store_true")
    p_chat.set_defaults(func=cmd_chat)

    p_q = sub.add_parser("query", help="POST /v2/agent/query (x-api-key)")
    _add_common(p_q)
    p_q.add_argument("text", help="Query string")
    p_q.add_argument("--user-id", default="agent-client")
    p_q.add_argument("--lang", default="EN", choices=["EN", "BM"])
    p_q.add_argument("--api-key", default=DEFAULT_API_KEY)
    p_q.set_defaults(func=cmd_query)

    p_s = sub.add_parser("search", help="POST /v2/agent/search (x-api-key)")
    _add_common(p_s)
    p_s.add_argument("text", help="Query string")
    p_s.add_argument("--user-id", default="agent-client")
    p_s.add_argument("--lang", default="EN", choices=["EN", "BM"])
    p_s.add_argument("--api-key", default=DEFAULT_API_KEY)
    p_s.set_defaults(func=cmd_search)

    p_ad = sub.add_parser("admin", help="Admin endpoints (ADMIN_TOKEN)")
    _add_common(p_ad)
    p_ad.add_argument(
        "admin_cmd",
        choices=["refresh-sop", "reset-memory", "tech-backlog-tabs"],
    )
    p_ad.add_argument("--phone", default=DEFAULT_PHONE, help="user_id for reset-memory")
    p_ad.set_defaults(func=cmd_admin)

    return ap


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
