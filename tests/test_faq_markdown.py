import unittest

from core.faq_markdown import parse_faq_markdown, replace_sop_sync_region, render_qas_markdown


class FaqMarkdownTests(unittest.TestCase):
    def test_parse_sections(self):
        text = "# intro\n\n## Q one\n\nA1\n\n## Q two\n\nA2\n"
        qas = parse_faq_markdown(text)
        self.assertEqual(len(qas), 2)
        self.assertEqual(qas[0]["question"], "Q one")
        self.assertEqual(qas[0]["answer"], "A1")

    def test_sync_replace(self):
        full = "before\n<!-- sop-sync:start -->\nold\n<!-- sop-sync:end -->\nafter"
        qas = [{"question": "NQ", "answer": "NA"}]
        inner = render_qas_markdown(qas)
        out = replace_sop_sync_region(full, inner)
        self.assertIn("## NQ", out)
        self.assertIn("NA", out)
        self.assertNotIn("old", out)


if __name__ == "__main__":
    unittest.main()
