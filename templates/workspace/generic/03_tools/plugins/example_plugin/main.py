#!/usr/bin/env python3
"""Example workspace plugin — prints JSON result to stdout (last JSON object wins)."""

from __future__ import annotations

import argparse
import json
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--visit-date", default="")
    parser.add_argument("--visit-time", default="")
    parser.add_argument("--unit-id", default="")
    args = parser.parse_args()
    payload = {
        "ok": True,
        "message": "example plugin stub",
        "visit_date": args.visit_date,
        "visit_time": args.visit_time,
        "unit_id": args.unit_id,
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
