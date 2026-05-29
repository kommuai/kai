#!/usr/bin/env python3
"""Minimal plugin for platform tests (no tenant coupling)."""
from __future__ import annotations

import argparse
import json
import sys


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--message", required=True)
    args = p.parse_args()
    print(json.dumps({"ok": True, "echo": args.message}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
