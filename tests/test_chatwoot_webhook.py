import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app import app

_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "chatwoot_agent_bot_incoming.json"


class ChatwootWebhookTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.payload = json.loads(_FIXTURE.read_text(encoding="utf-8"))

    @patch("kai.integrations.chatwoot.webhook.get_settings")
    def test_disabled_returns_503(self, gs_mock):
        gs_mock.return_value.kai_chatwoot_bot_enabled = False
        r = self.client.post("/webhooks/chatwoot", json=self.payload)
        self.assertEqual(r.status_code, 503)

    @patch("kai.integrations.chatwoot.webhook.get_settings")
    def test_invalid_secret_returns_401(self, gs_mock):
        s = gs_mock.return_value
        s.kai_chatwoot_bot_enabled = True
        s.kai_chatwoot_webhook_secret = "secret"
        s.kai_chatwoot_inbox_ids = ()
        r = self.client.post("/webhooks/chatwoot", json=self.payload)
        self.assertEqual(r.status_code, 401)

    @patch("kai.integrations.chatwoot.webhook.ChatwootClient")
    @patch("kai.integrations.chatwoot.webhook._process_agent_message_data")
    @patch("kai.integrations.chatwoot.webhook.try_mark_processed", return_value=True)
    @patch("kai.integrations.chatwoot.webhook.get_settings")
    def test_accepts_and_posts_reply(self, gs_mock, _mark, process_mock, client_mock):
        s = gs_mock.return_value
        s.kai_chatwoot_bot_enabled = True
        s.kai_chatwoot_webhook_secret = ""
        s.kai_chatwoot_inbox_ids = ()

        process_mock.return_value = {
            "type": "reply",
            "message": "Yes, you can install today.",
            "next_state": "bot",
        }
        client_mock.return_value.create_outgoing_message.return_value = (True, "")

        r = self.client.post(
            "/webhooks/chatwoot",
            json=self.payload,
            headers={"X-Chatwoot-Bot-Token": ""},
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json().get("accepted"))

        process_mock.assert_called_once()
        agent_data = process_mock.call_args[0][0]
        self.assertEqual(agent_data["phone_number"], "+60173611088")
        client_mock.return_value.create_outgoing_message.assert_called_once_with(
            "456",
            "Yes, you can install today.",
        )

    @patch("kai.integrations.chatwoot.webhook._process_agent_message_data")
    @patch("kai.integrations.chatwoot.webhook.try_mark_processed", return_value=False)
    @patch("kai.integrations.chatwoot.webhook.get_settings")
    def test_duplicate_skipped(self, gs_mock, _mark, process_mock):
        s = gs_mock.return_value
        s.kai_chatwoot_bot_enabled = True
        s.kai_chatwoot_webhook_secret = ""
        s.kai_chatwoot_inbox_ids = ()

        r = self.client.post("/webhooks/chatwoot", json=self.payload)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json().get("skipped"), "duplicate")
        process_mock.assert_not_called()

    @patch("kai.integrations.chatwoot.webhook._process_agent_message_data")
    @patch("kai.integrations.chatwoot.webhook.try_mark_processed", return_value=True)
    @patch("kai.integrations.chatwoot.webhook.get_settings")
    def test_frozen_does_not_post(self, gs_mock, _mark, process_mock):
        s = gs_mock.return_value
        s.kai_chatwoot_bot_enabled = True
        s.kai_chatwoot_webhook_secret = ""
        s.kai_chatwoot_inbox_ids = ()
        process_mock.return_value = {"type": "frozen", "message": "", "next_state": "human"}

        with patch("kai.integrations.chatwoot.webhook.ChatwootClient") as client_mock:
            r = self.client.post("/webhooks/chatwoot", json=self.payload)
            self.assertEqual(r.status_code, 200)
            client_mock.return_value.create_outgoing_message.assert_not_called()


if __name__ == "__main__":
    unittest.main()
