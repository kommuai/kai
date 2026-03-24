import tempfile
import unittest
from pathlib import Path

from config import _manifest_rag_source, resolve_master_faq_path


class WorkspaceContextResolutionTests(unittest.TestCase):
    def test_manifest_rag_source_parser(self):
        with tempfile.TemporaryDirectory() as td:
            manifest = Path(td) / "00_manifest.md"
            manifest.write_text(
                '---\nrag_source: 02_knowledge/faq/master_faq.md\n---\n',
                encoding="utf-8",
            )
            out = _manifest_rag_source(str(manifest))
            self.assertEqual(out, "02_knowledge/faq/master_faq.md")

    def test_resolve_master_faq_path_returns_string(self):
        out = resolve_master_faq_path()
        self.assertIsInstance(out, str)
        self.assertTrue(out.endswith(".md"))


if __name__ == "__main__":
    unittest.main()
