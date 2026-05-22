"""Phase 1: turn memory injection, topic stickiness, session FTS search."""

from __future__ import annotations

import os
import tempfile
import unittest
from uuid import uuid4

from kai.lib.context_memory import build_turn_memory_block
from kai.lib.session_search import index_message, search_user_messages
from kai.lib.session_state import (
    add_message_to_history,
    get_session_topics,
    init_db,
    reset_memory,
    update_session_topics,
)
from kai.support_runtime.agent_loop import AgentLoopDependencies, ReActAgentLoop
from kai.support_runtime.agent_tools import AgentToolRegistry
from kai.support_runtime.clarify_intent import pick_clarify_for_intent
from kai.support_runtime.retrieval import HybridRetriever, SimpleReranker


class Phase1ContextTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._db = os.path.join(self._tmpdir, "test_sessions.db")
        os.environ["SESSION_DB_PATH"] = self._db
        init_db()
        self.uid = f"p1_{uuid4().hex[:8]}"
        reset_memory(self.uid)

    def test_update_session_topics_vehicle(self):
        update_session_topics(self.uid, "Can 2021 Corolla Cross Hybrid install kommu?")
        topics = get_session_topics(self.uid)
        self.assertEqual(topics.get("last_topic"), "vehicle_support")
        self.assertIn("corolla", (topics.get("last_vehicle") or "").lower())

    def test_clarify_skips_year_when_vehicle_known(self):
        q = pick_clarify_for_intent(
            "Yes it has TSS2.0",
            "EN",
            session_topics={
                "last_topic": "vehicle_support",
                "last_vehicle": "2021 Corolla Cross Hybrid",
                "last_vehicle_year": "2021",
            },
        )
        self.assertIn("check", q.lower())
        self.assertNotIn("what year is your car", q.lower())

    def test_turn_memory_block_wraps_kai_session_context(self):
        update_session_topics(self.uid, "Corolla Cross 2021")
        block = build_turn_memory_block(self.uid, extra="FAQ hint here")
        self.assertIn("<kai-session-context>", block)
        self.assertIn("Corolla", block)
        self.assertIn("FAQ hint", block)

    def test_agent_loop_injects_turn_memory_on_user_message(self):
        prov = _CaptureProvider(
            '{"action":"final","decision":"direct_answer","answer":"ok","confidence":0.9,'
            '"source_ids":["intent:test"]}'
        )
        registry = AgentToolRegistry(HybridRetriever(provider=None), SimpleReranker(provider=None))
        loop = ReActAgentLoop(
            AgentLoopDependencies(provider=prov, tools=registry, system_prompt="SYS")
        )
        loop.run(
            text="supported?",
            turn_memory="<kai-session-context>\nVehicle: Corolla Cross\n</kai-session-context>",
            session_topics={"last_vehicle": "Corolla Cross 2021"},
        )
        user_msgs = [m for m in prov.last_messages if m["role"] == "user"]
        self.assertEqual(len(user_msgs), 1)
        self.assertIn("<kai-session-context>", user_msgs[0]["content"])
        self.assertIn("supported?", user_msgs[0]["content"])

    def test_session_search_indexes_and_finds(self):
        index_message(self.uid, "user", "2021 Corolla Cross hybrid supported or not")
        index_message(self.uid, "assistant", "Checking official support list")
        out = search_user_messages(self.uid, "corolla cross hybrid", limit=3)
        self.assertTrue(out.get("ok"))
        self.assertGreaterEqual(len(out.get("results") or []), 1)

    def test_search_session_memory_tool_scoped_to_user(self):
        registry = AgentToolRegistry(HybridRetriever(provider=None), SimpleReranker(provider=None))
        add_message_to_history(self.uid, "user", "dongle ABC12345 warranty")
        registry.set_context(user_id=self.uid)
        out = registry.search_session_memory(query="warranty dongle", limit=5)
        self.assertTrue(out.get("ok"))
        self.assertTrue(any("ABC12345" in (r.get("snippet") or "") for r in out.get("results") or []))


class _CaptureProvider:
    def __init__(self, response: str):
        self.response = response
        self.last_messages: list[dict] = []

    def chat_messages(self, messages, temperature=0.2, max_tokens=1200):
        self.last_messages = list(messages)
        return self.response


if __name__ == "__main__":
    unittest.main()
