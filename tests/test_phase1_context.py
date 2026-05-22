"""Session-scoped chat + FTS search (regex topic stickiness removed)."""

from __future__ import annotations

import os
import tempfile
import unittest
from uuid import uuid4

from kai.lib.context_memory import build_turn_memory_block
from kai.lib.session_search import index_message, search_user_messages
from kai.lib.session_state import (
    add_message_to_history,
    get_history,
    init_db,
    reset_memory,
)
from kai.support_runtime.agent_loop import AgentLoopDependencies, ReActAgentLoop
from kai.support_runtime.agent_tools import AgentToolRegistry
from kai.support_runtime.faq_context import master_faq_system_block
from kai.support_runtime.retrieval import HybridRetriever, SimpleReranker


class Phase1ContextTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._db = os.path.join(self._tmpdir, "test_sessions.db")
        os.environ["SESSION_DB_PATH"] = self._db
        init_db()
        self.uid = f"p1_{uuid4().hex[:8]}"
        reset_memory(self.uid)

    def test_turn_memory_block_deprecated_empty(self):
        self.assertEqual(build_turn_memory_block(self.uid, extra="FAQ hint"), "")

    def test_full_session_history_not_capped_at_10(self):
        for i in range(15):
            add_message_to_history(self.uid, "user", f"m{i}")
        hist = get_history(self.uid)
        self.assertEqual(len(hist), 15)
        self.assertEqual(hist[0]["text"], "m0")
        self.assertEqual(hist[-1]["text"], "m14")

    def test_agent_loop_includes_all_history_in_messages(self):
        add_message_to_history(self.uid, "user", "installer in penang?")
        add_message_to_history(self.uid, "assistant", "postcode?")
        prov = _CaptureProvider(
            '{"action":"final","decision":"direct_answer","answer":"ok","confidence":0.9}'
        )
        registry = AgentToolRegistry(HybridRetriever(provider=None), SimpleReranker(provider=None))
        loop = ReActAgentLoop(
            AgentLoopDependencies(provider=prov, tools=registry, system_prompt="SYS")
        )
        loop.run(text="10200", conversation_history=get_history(self.uid))
        roles = [m["role"] for m in prov.last_messages]
        self.assertEqual(roles.count("user"), 2)
        self.assertEqual(roles.count("assistant"), 1)

    def test_master_faq_block_non_empty(self):
        block = master_faq_system_block()
        self.assertIn("Authoritative FAQ", block)
        self.assertIn("regional_installer", block.lower())

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
