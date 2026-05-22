# Hermes adoption — Phase 1 (context)

Implemented 2026-05-22. Reference: `workspace/hermes-agent` memory patterns.

## Goals

1. Richer session context on every ReAct turn (Hermes-style **ephemeral user-turn injection**).
2. **Topic stickiness** so the bot does not re-ask year/model when already in thread.
3. **`search_session_memory`** tool — FTS over this user's prior messages (not cross-user).

## Components

| Piece | Path |
|-------|------|
| Turn memory wrapper | `kai/lib/context_memory.py` → `build_turn_memory_block()` |
| Topic fields | `session_state`: `last_topic`, `last_vehicle`, `last_vehicle_year`, `last_dongle` |
| Message FTS index | `kai/lib/session_search.py` |
| ReAct injection | `kai/support_runtime/agent_loop.py` — `<kai-session-context>` on user message |
| Tool | `search_session_memory` in `agent_tools.py` |
| Vehicle tool nudge | Ungrounded `direct_answer` on vehicle thread → force `search_kommu_support` step |

## Flow

```
execute()
  → update_session_topics(user)
  → add_message_to_history (+ FTS index)
  → build_turn_memory_block(user, extra=canonical FAQ hint)
  → graph.run(turn_memory=..., session_topics=...)
```

## Privacy

Session search is **scoped to the current `user_id` (phone)** only. No cross-customer recall in Phase 1.

## Next (Phase 2)

Background FAQ review after handback, `learn_queue/`, approved merge into `master_faq.md`.
