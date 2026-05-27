import json
import unittest
from pathlib import Path

from kai.integrations.chatwoot.mapper import (
    map_chatwoot_event_to_agent_data,
    should_skip_event,
)

_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "chatwoot_agent_bot_incoming.json"


class ChatwootMapperTests(unittest.TestCase):
    def _payload(self) -> dict:
        return json.loads(_FIXTURE.read_text(encoding="utf-8"))

    def test_maps_incoming_to_agent_data(self):
        out = map_chatwoot_event_to_agent_data(self._payload())
        self.assertIsNotNone(out)
        assert out is not None
        self.assertEqual(out["phone_number"], "+60173611088")
        self.assertEqual(out["content"], "Can I install today?")
        self.assertEqual(out["conversation_id"], 456)

    def test_phone_canonical_from_plus60(self):
        payload = self._payload()
        payload["conversation"]["meta"]["sender"]["phone_number"] = "+60173611088"
        out = map_chatwoot_event_to_agent_data(payload)
        self.assertEqual(out["phone_number"], "+60173611088")

    def test_skip_outgoing(self):
        payload = self._payload()
        payload["message"]["message_type"] = "outgoing"
        skip, reason = should_skip_event(payload, allowed_inbox_ids=())
        self.assertTrue(skip)
        self.assertIn("not_incoming", reason)

    def test_skip_agent_sender(self):
        payload = self._payload()
        payload["message"]["sender"]["type"] = "user"
        skip, reason = should_skip_event(payload, allowed_inbox_ids=())
        self.assertTrue(skip)
        self.assertIn("sender_not_contact", reason)

    def test_skip_private(self):
        payload = self._payload()
        payload["message"]["private"] = True
        skip, _ = should_skip_event(payload, allowed_inbox_ids=())
        self.assertTrue(skip)

    def test_inbox_allowlist(self):
        payload = self._payload()
        skip, _ = should_skip_event(payload, allowed_inbox_ids=(12,))
        self.assertFalse(skip)
        skip2, reason2 = should_skip_event(payload, allowed_inbox_ids=(99,))
        self.assertTrue(skip2)
        self.assertIn("inbox_not_allowed", reason2)


if __name__ == "__main__":
    unittest.main()
