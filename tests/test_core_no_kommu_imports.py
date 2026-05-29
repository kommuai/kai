"""Core support_runtime must not hardcode Kommu product ids or URLs."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1] / "kai" / "support_runtime"
_FORBIDDEN = re.compile(
    r"search_kommu_support|kommu\.ai|kommuai/bukapilot",
    re.I,
)
_ALLOWLIST_FILES = frozenset(
    {
        # display_name-driven branding only; no hardcoded Kommu URLs in core handlers
    }
)


class CoreNoKommuImportsTests(unittest.TestCase):
    def test_support_runtime_py_files_have_no_kommu_coupling(self) -> None:
        offenders: list[str] = []
        for path in sorted(_ROOT.rglob("*.py")):
            if path.name in _ALLOWLIST_FILES:
                continue
            text = path.read_text(encoding="utf-8")
            if _FORBIDDEN.search(text):
                offenders.append(str(path.relative_to(_ROOT.parents[1])))
        self.assertEqual(offenders, [], f"Kommu-specific strings in core: {offenders}")


if __name__ == "__main__":
    unittest.main()
