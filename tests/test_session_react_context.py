"""Session follow-up routing: ReAct loop uses full chat history."""

from __future__ import annotations

import unittest
from uuid import uuid4

from kai.lib.session_state import add_message_to_history, init_db, reset_memory
from kai.support_runtime.service import SupportRuntimeService


class SessionReactContextTests(unittest.TestCase):
    def setUp(self):
        init_db()
        self.uid = f"sess_{uuid4().hex[:8]}"
        reset_memory(self.uid)

    def test_follow_up_uses_react_not_faq_first_shelf(self):
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
