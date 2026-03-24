import unittest

from core.faq_markdown import (
    parse_faq_markdown,
    parse_master_faq_schema,
    replace_sop_sync_region,
    render_qas_markdown,
)


class FaqMarkdownTests(unittest.TestCase):
    def test_parse_sections(self):
        text = (
            "# intro\n\n"
            "## intent: q_one\n"
            "aliases:\n- Q one\n"
            "answer:\nA1\n\n"
            "## intent: q_two\n"
            "answer:\nA2\n"
        )
        qas = parse_faq_markdown(text)
        self.assertEqual(len(qas), 2)
        self.assertEqual(qas[0]["question"], "Q one")
        self.assertEqual(qas[0]["answer"], "A1")

    def test_parse_master_schema_workflow_data(self):
        text = (
            "## workflow: repair_flow\n"
            "steps:\n1. check warranty\n2. quote\n\n"
            "## data: bank\n"
            "name: Kommu\n"
        )
        parsed = parse_master_faq_schema(text)
        self.assertEqual(parsed["workflows"][0]["workflow_id"], "repair_flow")
        self.assertEqual(parsed["data"][0]["name"], "bank")

    def test_sync_replace(self):
        full = "before\n<!-- sop-sync:start -->\nold\n<!-- sop-sync:end -->\nafter"
        qas = [{"question": "NQ", "answer": "NA"}]
        inner = render_qas_markdown(qas)
        out = replace_sop_sync_region(full, inner)
        self.assertIn("## intent:", out)
        self.assertIn("aliases:", out)
        self.assertIn("NA", out)
        self.assertNotIn("old", out)


if __name__ == "__main__":
    unittest.main()
