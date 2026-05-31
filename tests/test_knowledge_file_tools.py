"""Phase 2-A: Knowledge file tools — read-only, path-scoped."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from shadou.support_runtime.tools.knowledge_file_tools import (
    extract_frontmatter,
    get_file_outline,
    grep_knowledge,
    list_knowledge_files,
    read_knowledge_lines,
    read_knowledge_section,
)


def _make_fixture(tmp: Path) -> Path:
    """Create a minimal knowledge directory with some Markdown files."""
    knowledge = tmp / "knowledge"
    knowledge.mkdir()

    (knowledge / "product.md").write_text(
        "---\ntitle: Product Guide\nauthor: test\n---\n"
        "# Product Guide\n\n## Overview\nThis is the product overview.\n\n"
        "## Pricing\nThe price is RM200.\n\n"
        "## Warranty\nWarranty is 12 months.\n",
        encoding="utf-8",
    )
    (knowledge / "faq.md").write_text(
        "# FAQ\n\n## intent: greeting\nHow can I help?\n\n## intent: pricing\nRM200 per unit.\n",
        encoding="utf-8",
    )
    sub = knowledge / "sub"
    sub.mkdir()
    (sub / "deep.md").write_text("# Deep\nSome nested content.\n", encoding="utf-8")
    return knowledge


def _clear_settings_cache() -> None:
    try:
        from shadou.settings import get_settings
        get_settings.cache_clear()  # type: ignore[attr-defined]
    except Exception:
        pass


class ListKnowledgeFilesTests(unittest.TestCase):
    def setUp(self):
        _clear_settings_cache()
        self._tmp = Path(tempfile.mkdtemp())
        self._knowledge = _make_fixture(self._tmp)
        os.environ["SHADOU_HOME"] = str(self._tmp)

    def tearDown(self):
        os.environ.pop("SHADOU_HOME", None)
        _clear_settings_cache()

    def test_lists_md_files(self):
        result = list_knowledge_files()
        self.assertTrue(result["ok"])
        self.assertGreater(result["count"], 0)
        names = [f for f in result["files"]]
        self.assertTrue(any("product.md" in f for f in names))
        self.assertTrue(any("faq.md" in f for f in names))

    def test_glob_filters_work(self):
        result = list_knowledge_files(glob="sub/**/*.md")
        self.assertTrue(result["ok"])
        self.assertTrue(all("deep" in f or "sub" in f for f in result["files"]))

    def test_empty_directory(self):
        empty = self._tmp / "knowledge"
        for f in empty.rglob("*"):
            if f.is_file():
                f.unlink()
        result = list_knowledge_files()
        self.assertTrue(result["ok"])
        self.assertEqual(result["count"], 0)


class ReadKnowledgeLinesTests(unittest.TestCase):
    def setUp(self):
        _clear_settings_cache()
        self._tmp = Path(tempfile.mkdtemp())
        _make_fixture(self._tmp)
        os.environ["SHADOU_HOME"] = str(self._tmp)

    def tearDown(self):
        os.environ.pop("SHADOU_HOME", None)
        _clear_settings_cache()

    def test_reads_valid_range(self):
        result = read_knowledge_lines("product.md", start=1, end=3)
        self.assertTrue(result["ok"])
        self.assertIn("content", result)
        self.assertGreater(len(result["content"]), 0)

    def test_file_not_found(self):
        result = read_knowledge_lines("nonexistent.md", start=1, end=5)
        self.assertFalse(result["ok"])
        self.assertIn("error", result)

    def test_path_traversal_denied(self):
        result = read_knowledge_lines("../../etc/passwd", start=1, end=5)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "access_denied")

    def test_hard_cap_enforced(self):
        result = read_knowledge_lines("product.md", start=1, end=10000)
        self.assertTrue(result["ok"])
        lines = result["content"].splitlines()
        self.assertLessEqual(len(lines), 501)


class GrepKnowledgeTests(unittest.TestCase):
    def setUp(self):
        _clear_settings_cache()
        self._tmp = Path(tempfile.mkdtemp())
        _make_fixture(self._tmp)
        os.environ["SHADOU_HOME"] = str(self._tmp)

    def tearDown(self):
        os.environ.pop("SHADOU_HOME", None)
        _clear_settings_cache()

    def test_finds_known_string(self):
        result = grep_knowledge("RM200")
        self.assertTrue(result["ok"])
        self.assertGreater(result["count"], 0)
        self.assertTrue(any("RM200" in h["line"] for h in result["hits"]))

    def test_finds_with_line_number(self):
        result = grep_knowledge("Warranty")
        self.assertTrue(result["ok"])
        for hit in result["hits"]:
            self.assertIn("line_number", hit)
            self.assertIsInstance(hit["line_number"], int)

    def test_no_match_returns_empty_hits(self):
        result = grep_knowledge("XYZZY_NEVER_EXISTS_IN_FIXTURE")
        self.assertTrue(result["ok"])
        self.assertEqual(result["count"], 0)

    def test_invalid_regex_returns_error(self):
        result = grep_knowledge("[unclosed", literal=False)
        self.assertFalse(result["ok"])
        self.assertIn("invalid_pattern", result["error"])

    def test_missing_pattern_returns_error(self):
        result = grep_knowledge("")
        self.assertFalse(result["ok"])


class GetFileOutlineTests(unittest.TestCase):
    def setUp(self):
        _clear_settings_cache()
        self._tmp = Path(tempfile.mkdtemp())
        _make_fixture(self._tmp)
        os.environ["SHADOU_HOME"] = str(self._tmp)

    def tearDown(self):
        os.environ.pop("SHADOU_HOME", None)
        _clear_settings_cache()

    def test_returns_heading_tree(self):
        result = get_file_outline("product.md")
        self.assertTrue(result["ok"])
        titles = [h["title"] for h in result["headings"]]
        self.assertIn("Product Guide", titles)
        self.assertIn("Overview", titles)

    def test_levels_are_correct(self):
        result = get_file_outline("product.md")
        h1 = [h for h in result["headings"] if h["level"] == 1]
        h2 = [h for h in result["headings"] if h["level"] == 2]
        self.assertEqual(len(h1), 1)
        self.assertGreater(len(h2), 1)

    def test_file_not_found(self):
        result = get_file_outline("missing.md")
        self.assertFalse(result["ok"])


class ReadKnowledgeSectionTests(unittest.TestCase):
    def setUp(self):
        _clear_settings_cache()
        self._tmp = Path(tempfile.mkdtemp())
        _make_fixture(self._tmp)
        os.environ["SHADOU_HOME"] = str(self._tmp)

    def tearDown(self):
        os.environ.pop("SHADOU_HOME", None)
        _clear_settings_cache()

    def test_reads_correct_section(self):
        result = read_knowledge_section("product.md", "Pricing")
        self.assertTrue(result["ok"])
        self.assertIn("RM200", result["content"])
        self.assertNotIn("Warranty", result["content"])

    def test_heading_not_found(self):
        result = read_knowledge_section("product.md", "NonExistentSection")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "heading_not_found")

    def test_missing_heading_arg(self):
        result = read_knowledge_section("product.md", "")
        self.assertFalse(result["ok"])


class ExtractFrontmatterTests(unittest.TestCase):
    def setUp(self):
        _clear_settings_cache()
        self._tmp = Path(tempfile.mkdtemp())
        _make_fixture(self._tmp)
        os.environ["SHADOU_HOME"] = str(self._tmp)

    def tearDown(self):
        os.environ.pop("SHADOU_HOME", None)
        _clear_settings_cache()

    def test_extracts_frontmatter(self):
        result = extract_frontmatter("product.md")
        self.assertTrue(result["ok"])
        self.assertTrue(result["has_frontmatter"])
        self.assertEqual(result["frontmatter"].get("title"), "Product Guide")

    def test_no_frontmatter_returns_empty_dict(self):
        result = extract_frontmatter("sub/deep.md")
        self.assertTrue(result["ok"])
        self.assertFalse(result["has_frontmatter"])
        self.assertEqual(result["frontmatter"], {})

    def test_file_not_found(self):
        result = extract_frontmatter("missing.md")
        self.assertFalse(result["ok"])

    def test_path_traversal_denied(self):
        result = extract_frontmatter("../../etc/hosts")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "access_denied")


if __name__ == "__main__":
    unittest.main()
