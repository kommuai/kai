"""Example plugin — JSON stdin/stdout contract."""
import json
import sys


def main():
    req = json.load(sys.stdin)
    args = req.get("args") or {}
    print(json.dumps({"ok": True, "result": {"echo": args}}))


if __name__ == "__main__":
    main()
