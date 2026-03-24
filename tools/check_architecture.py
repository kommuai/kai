#!/usr/bin/env python3
from pathlib import Path
import sys


def main() -> int:
    violations: list[str] = []
    root = Path(".")
    for py in root.rglob("*.py"):
        text = py.read_text(encoding="utf-8", errors="ignore")
        if py.as_posix().startswith("core/router/") and "from skills." in text:
            violations.append(f"{py}: router must not import skills directly")
    if violations:
        print("Architecture violations:")
        for item in violations:
            print(f"- {item}")
        return 1
    print("Architecture checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

