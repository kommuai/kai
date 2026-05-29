#!/usr/bin/env python3
"""Example plugin — deterministic CLI + JSON stdout contract."""
from __future__ import annotations

import argparse
import json
import sys


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="example_plugin")
    p.add_argument("--query", required=True, help="Echo input")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    query = (args.query or "").strip()
    if not query:
        print(json.dumps({"ok": False, "error": "missing_query"}))
        return 1
    print(json.dumps({"ok": True, "result": {"echo": query}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(1)
