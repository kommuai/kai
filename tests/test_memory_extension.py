import time
import unittest

from session_state import (
    add_message_to_history,
    extract_and_store_facts,
    get_history,
    get_memory_facts,
    get_session_summary,
    init_db,
    reset_memory,
    update_session_summary,
    upsert_memory_fact,
    prune_expired_memory_facts,
)


class MemoryExtensionTests(unittest.TestCase):
    def setUp(self):
        init_db()
        self.uid = "mem_test_user"
        reset_memory(self.uid)

    def test_history_window_10(self):
        for i in range(13):
            add_message_to_history(self.uid, "user", f"m{i}")
        hist = get_history(self.uid)
        self.assertEqual(len(hist), 10)
        self.assertEqual(hist[0]["text"], "m3")
        self.assertEqual(hist[-1]["text"], "m12")

    def test_session_summary_persists(self):
        update_session_summary(self.uid, "user", "my name is Alex")
        update_session_summary(self.uid, "bot", "hi alex")
        s = get_session_summary(self.uid)
        self.assertIn("User: my name is Alex", s)
        self.assertIn("Bot: hi alex", s)

    def test_fact_extraction_and_storage(self):
        extract_and_store_facts(self.uid, "my name is Alice and i drive Honda City", source="user")
        facts = get_memory_facts(self.uid)
        keys = {(f["fact_type"], f["fact_key"]) for f in facts}
        self.assertIn(("identity", "name"), keys)
        self.assertIn(("device_account", "car_owned"), keys)
        self.assertIn(("device_account", "phone_number"), keys)

    def test_ttl_refresh_on_seen(self):
        upsert_memory_fact(self.uid, "temporary_issue", "active_issue", "error 1003", "user", 7)
        first = get_memory_facts(self.uid, "temporary_issue")[0]["expires_at"]
        time.sleep(0.01)
        upsert_memory_fact(self.uid, "temporary_issue", "active_issue", "error 1003", "user", 7)
        second = get_memory_facts(self.uid, "temporary_issue")[0]["expires_at"]
        self.assertGreater(second, first)

    def test_expiry_pruning(self):
        upsert_memory_fact(self.uid, "temporary_issue", "active_issue", "error now", "user", -1)
        prune_expired_memory_facts(self.uid)
        facts = get_memory_facts(self.uid, "temporary_issue")
        self.assertEqual(len(facts), 0)


if __name__ == "__main__":
    unittest.main()
