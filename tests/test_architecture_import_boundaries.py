from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_DIRS = ("api", "support_runtime", "services", "core")
DISALLOWED_IMPORT_SNIPPETS = (
    "archive_legacy.",
    "from archive_legacy",
    "import archive_legacy",
    "from core.policy.tool_adapter",
    "from core.skills.registry",
)


class ArchitectureImportBoundaryTests(unittest.TestCase):
    def test_active_runtime_does_not_import_archived_or_removed_modules(self):
        violations: list[str] = []
        for rel in ACTIVE_DIRS:
            base = ROOT / rel
            if not base.exists():
                continue
            for py in base.rglob("*.py"):
                text = py.read_text(encoding="utf-8", errors="ignore")
                for snippet in DISALLOWED_IMPORT_SNIPPETS:
                    if snippet in text:
                        violations.append(f"{py.relative_to(ROOT)} uses '{snippet}'")
        self.assertEqual([], violations, "\n".join(violations))


if __name__ == "__main__":
    unittest.main()
