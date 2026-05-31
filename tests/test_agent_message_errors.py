import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import app
from shadou.support_runtime.models import RuntimeResult


class AgentMessageErrorTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch("shadou.api.v2.agent_message.shadou_service.pre_router", return_value=None)
    @patch("shadou.api.v2.agent_message.support_runtime_service.execute")
    def test_runtime_exception_returns_safe_reply(self, execute_mock, _pre):
        execute_mock.side_effect = RuntimeError("llm down")
        resp = self.client.post(
            "/v2/agent/message",
            json={"phone_number": "err_u1", "content": "hello"},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body.get("type"), "reply")
        self.assertIn("something went wrong", body.get("message", "").lower())
        self.assertNotIn("debug", body)

    @patch("shadou.api.v2.agent_message.shadou_service.pre_router", return_value=None)
    @patch("shadou.api.v2.agent_message.support_runtime_service.execute")
    @patch("shadou.api.v2.agent_message.get_settings")
    def test_debug_requires_admin_when_env_enabled(self, gs_mock, execute_mock, _pre):
        from unittest.mock import Mock

        s = Mock()
        s.shadou_route_agent_debug_enabled = True
        s.admin_token = "changeme-strong"
        gs_mock.return_value = s
        execute_mock.return_value = RuntimeResult(
            decision="direct_answer",
            answer="ok",
            confidence=0.9,
            metadata={"agentic_route": {"steps": 1}},
        )
        resp = self.client.post(
            "/v2/agent/message",
            json={
                "phone_number": "dbg_u1",
                "content": "hi",
                "debug_route_agent": True,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("debug", resp.json())

        resp2 = self.client.post(
            "/v2/agent/message",
            json={"phone_number": "dbg_u2", "content": "hi", "debug_route_agent": True},
            headers={"x-admin-token": s.admin_token},
        )
        self.assertIn("debug", resp2.json())


if __name__ == "__main__":
    unittest.main()
