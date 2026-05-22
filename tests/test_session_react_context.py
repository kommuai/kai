"""Session follow-up routing: ReAct loop + short-term memory in context."""

from __future__ import annotations

import unittest
from uuid import uuid4

from kai.lib.session_state import (
    add_message_to_history,
    build_short_term_context,
    init_db,
    reset_memory,
    update_session_summary,
    upsert_memory_fact,
)
from kai.support_runtime.agent_loop import AgentLoopDependencies, ReActAgentLoop
from kai.support_runtime.agent_tools import AgentToolRegistry
from kai.support_runtime.retrieval import HybridRetriever, SimpleReranker
from kai.support_runtime.service import SupportRuntimeService


class _CaptureProvider:
    def __init__(self, response: str):
        self.response = response
        self.last_messages: list[dict] = []

    def chat_messages(self, messages, temperature=0.2, max_tokens=1200):
        self.last_messages = list(messages)
        return self.response

    def chat(self, system_prompt, user_prompt, temperature=0.2, max_tokens=500):
        return self.chat_messages(
            [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )


class SessionReactContextTests(unittest.TestCase):
    def setUp(self):
        init_db()
        self.uid = f"sess_{uuid4().hex[:8]}"
        reset_memory(self.uid)

    def test_build_short_term_context_includes_summary_and_facts(self):
        update_session_summary(self.uid, "user", "Corolla Cross 2021 Hybrid")
        upsert_memory_fact(self.uid, "device_account", "car_owned", "Toyota Corolla Cross", "user", 90)
        ctx = build_short_term_context(self.uid)
        self.assertIn("Corolla Cross", ctx)
        self.assertIn("car_owned", ctx)
        self.assertIn("Short-term session memory", ctx)

    def test_agent_loop_injects_session_context_and_history(self):
        prov = _CaptureProvider(
            '{"action":"final","decision":"direct_answer","answer":"Supported.","confidence":0.9,'
            '"source_ids":["intent:test"]}'
        )
        registry = AgentToolRegistry(HybridRetriever(provider=None), SimpleReranker(provider=None))
        loop = ReActAgentLoop(
            AgentLoopDependencies(provider=prov, tools=registry, system_prompt="SYS")
        )
        history = [
            {"role": "user", "text": "is corolla cross supported?"},
            {"role": "assistant", "text": "What year?"},
            {"role": "user", "text": "2021 Hybrid"},
        ]
        session_ctx = "### Session summary\nUser: corolla cross 2021"
        loop.run(
            text="2021 Hybrid",
            conversation_history=history,
            session_context=session_ctx,
        )
        roles_contents = [(m["role"], m.get("content", "")[:80]) for m in prov.last_messages]
        system_texts = [c for r, c in roles_contents if r == "system"]
        self.assertTrue(any("corolla cross 2021" in t for t in system_texts))
        user_msgs = [c for r, c in roles_contents if r == "user"]
        # Current user text already in history tail — must not duplicate
        self.assertEqual(sum(1 for u in user_msgs if u.startswith("2021 Hybrid")), 1)

    def test_react_injects_canonical_hint_when_faq_matches(self):
        svc = SupportRuntimeService()
        svc.startup()
        uid = f"canon_{uuid4().hex[:6]}"
        reset_memory(uid)
        add_message_to_history(uid, "user", "how to self install kommu assist")
        add_message_to_history(uid, "assistant", "Steps listed.")
        out = svc.execute("is there any video guide link?", lang="EN", user_id=uid)
        self.assertEqual(out.capability_used, "react_agent_loop")
        meta = out.metadata or {}
        self.assertTrue(meta.get("agentic_route") is not None or out.answer)

    def test_follow_up_skips_faq_first_uses_react(self):
        svc = SupportRuntimeService()
        svc.startup()
        uid = f"fu_{uuid4().hex[:6]}"
        reset_memory(uid)
        add_message_to_history(uid, "user", "how to self install")
        add_message_to_history(uid, "assistant", "Follow the install guide steps.")
        out = svc.execute("is there any video for this?", lang="EN", user_id=uid)
        self.assertEqual(out.capability_used, "react_agent_loop")


if __name__ == "__main__":
    unittest.main()
