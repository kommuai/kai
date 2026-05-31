import unittest

from shadou.core.faq_markdown import (
    normalize_intent_block,
    parse_faq_markdown,
    parse_master_faq_schema,
    replace_sop_sync_region,
    render_qas_markdown,
    upsert_intent_block,
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

    def test_upsert_intent_replaces_existing_block(self):
        text = (
            "# header\n\n"
            "## intent: old_one\n"
            "aliases:\n- one\n"
            "answer:\nA1\n\n"
            "## intent: keep_me\n"
            "answer:\nStay\n"
        )
        body = "aliases:\n- two\nanswer:\nA2\n"
        out = upsert_intent_block(text, "old_one", body)
        self.assertIn("A2", out)
        self.assertNotIn("A1", out)
        self.assertIn("Stay", out)
        parsed = parse_master_faq_schema(out)
        ids = [r["intent_id"] for r in parsed["intents"]]
        self.assertEqual(ids, ["old_one", "keep_me"])

    def test_upsert_intent_appends_inside_sop_sync(self):
        text = (
            "preamble\n<!-- sop-sync:start -->\n"
            "## intent: existing\nanswer:\nHi\n"
            "<!-- sop-sync:end -->\n"
        )
        out = upsert_intent_block(text, "new_one", "aliases:\n- n\nanswer:\nNew\n")
        self.assertIn("## intent: new_one", out)
        self.assertIn("New", out)
        self.assertIn("<!-- sop-sync:end -->", out)
        self.assertLess(out.index("new_one"), out.index("<!-- sop-sync:end -->"))

    def test_normalize_intent_block_requires_answer(self):
        with self.assertRaises(ValueError):
            normalize_intent_block("x", "aliases:\n- only\n")

    def test_dynamic_block_parses_lifespan_and_priority(self):
        text = (
            "## dynamic: batch_status\n"
            "batch: 4\n"
            "status: assembling\n"
            "valid_from: 2026-03-01\n"
            "valid_until: 2026-04-30\n"
            "priority: 10\n"
        )
        parsed = parse_master_faq_schema(text)
        self.assertEqual(len(parsed["dynamic"]), 1)
        d0 = parsed["dynamic"][0]
        self.assertEqual(d0["name"], "batch_status")
        self.assertEqual(d0["fields"]["batch"], "4")
        self.assertEqual(d0["valid_from"], "2026-03-01")
        self.assertEqual(d0["valid_until"], "2026-04-30")
        self.assertEqual(d0["priority"], 10)


if __name__ == "__main__":
    unittest.main()
