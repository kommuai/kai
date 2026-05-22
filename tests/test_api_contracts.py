import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.v2.agent_query import agent_query, agent_search, AgentQueryRequest
from app import app
from fastapi import HTTPException
from support_runtime.models import RuntimeResult


class AgentQueryContractTests(unittest.TestCase):
    @patch("api.v2.agent_query.authorize", return_value=False)
    def test_agent_query_requires_api_key(self, _auth):
        with self.assertRaises(HTTPException) as ctx:
            agent_query(AgentQueryRequest(query="hello"), x_api_key=None)
        self.assertEqual(ctx.exception.status_code, 401)

    @patch("api.v2.agent_query.authorize", return_value=True)
    @patch("api.v2.agent_query.support_runtime_service.execute")
    def test_agent_query_escalation_returns_404(self, execute_mock, _auth):
        execute_mock.return_value = RuntimeResult(
            decision="escalate_human",
            answer="Escalate",
            confidence=0.9,
            fallback_reason="needs_human",
        )
        with self.assertRaises(HTTPException) as ctx:
            agent_query(AgentQueryRequest(query="hard case"), x_api_key="k")
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail, "needs_human")

    @patch("api.v2.agent_query.authorize", return_value=True)
    @patch("api.v2.agent_query.support_runtime_service.execute")
    def test_agent_search_contract(self, execute_mock, _auth):
        execute_mock.return_value = RuntimeResult(
            decision="direct_answer",
            answer="ok",
            confidence=0.88,
            source_ids=["intent:install_booking"],
            capability_used="canonical_answer",
        )
        out = agent_search(AgentQueryRequest(query="can i install now"), x_api_key="k")
        self.assertIn("trace_id", out)
        self.assertEqual(out.get("capability_used"), "canonical_answer")
        self.assertEqual(len(out.get("sources", [])), 1)


class AgentMessageShadowContractTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch("api.v2.agent_message.kai_service.pre_router", return_value=None)
    @patch("api.v2.agent_message.support_runtime_service.execute")
    def test_v2_message_uses_support_runtime(self, execute_mock, _pre):
        execute_mock.return_value = RuntimeResult(
            decision="direct_answer",
            answer="Installation is by appointment after checkout.",
            confidence=0.9,
            source_ids=["intent:install_booking"],
            capability_used="canonical_answer",
        )
        resp = self.client.post("/v2/agent/message", json={"phone_number": "u_shadow_off", "content": "install now?"})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body.get("type"), "reply")
        execute_mock.assert_called_once()

    @patch("api.v2.agent_message._refresh_all_knowledge", return_value={"ok": True, "runtime_refresh": {"intents": 1}})
    def test_admin_refresh_sop_contract(self, refresh_mock):
        resp = self.client.post("/admin/refresh-sop", headers={"x-admin-token": "changeme-strong"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("ok"))
        refresh_mock.assert_called_once()

    def test_admin_refresh_sop_requires_admin_token(self):
        resp = self.client.post("/admin/refresh-sop")
        self.assertEqual(resp.status_code, 401)


if __name__ == "__main__":
    unittest.main()
