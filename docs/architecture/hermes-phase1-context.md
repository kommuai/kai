# Hermes adoption — Phase 1 (context)

Implemented 2026-05-22. Reference: `workspace/hermes-agent` memory patterns.

## Goals

1. Full session history on every ReAct turn (not capped at 10 messages).
2. Session summary + memory facts via `turn_ingest` / `session_state`.
3. **`search_session_memory`** tool — FTS over this user's prior messages (not cross-user).

## Components

| Piece | Path |
|-------|------|
| Turn ingest | `kai/services/turn_ingest.py` → `ingest_user_turn()` (summary + facts + optional history) |
| Memory facts | `session_state`: `extract_and_store_facts`, `get_memory_facts` |
| Message FTS index | `kai/lib/session_search.py` |
| ReAct injection | `kai/support_runtime/agent_loop.py` — full session history + `master_faq` in system prompt |
| Tool | `search_session_memory` in `agent_tools.py` |
| Vehicle tool nudge | Ungrounded `direct_answer` on vehicle thread → force `search_kommu_support` step |

## Flow

```
pre_router / execute
  → ingest_user_turn (summary, facts, history per path)
  → add_message_to_history (+ FTS index)
  → graph.run(history from session_state, full FAQ in system prompt)
```

## Privacy

Session search is **scoped to the current `user_id` (phone)** only. No cross-customer recall in Phase 1.

## Next (Phase 2)

Background FAQ review after handback, `learn_queue/`, approved merge into `master_faq.md`.
