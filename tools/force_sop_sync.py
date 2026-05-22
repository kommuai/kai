#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kai.core.sop_sync_merge import sync_sop_regions  # noqa: E402


def main() -> int:
    out = sync_sop_regions()
    print(json.dumps(out, indent=2, ensure_ascii=True))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
