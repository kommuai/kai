# Current architecture map

Production chat flow (WhatsApp / n8n):

```
POST /agent/message  (or /v2/agent/message)
  → KaiService.pre_router          # handover, frozen, session priming
  → SupportRuntimeService.execute  # FAQ-first + ReAct agent loop
  → outbound_delivery              # WhatsApp length cap (4096)
```

## Active packages

| Path | Role |
|------|------|
| `app.py` | FastAPI app, startup refresh, optional SOP merge cron |
| `api/v2/` | Chat + admin + agent query routes |
| `services/kai_service.py` | `pre_router`, footers, outbound prep |
| `support_runtime/` | Compiler, ReAct loop, agent tools, turn planner, evidence policy |
| `agent_workspace/` | FAQ markdown → `compiled/` JSON |
| `session_state.py` | SQLite sessions + memory facts |
| `core/outbound_delivery.py` | Intelligent reply shortening for Twilio |

## Removed (legacy cleanup)

- `archive_legacy/` — old RouterEngine + workspace skill loaders
- `KaiService.main_conversation` / `run_rag_dual` / `handle_agent_message`
- `support_runtime/router.py` (IntentRouter) — routing is FAQ-first + ReAct agent loop
- `support_runtime/tools.py` (ToolPolicyEngine) — unused in ReAct path
- `support_runtime/warranty.py` — warranty via `agent_tools.lookup_warranty`
- `templates.py`, `workers/skill_worker.py`
- Unused `agent_workspace/03_skills/*/handler.py` skill stubs

## Knowledge refresh

- `POST /admin/refresh-sop` → `compile_canonical_knowledge()` + warranty sheet load
- Optional daily SOP merge: `KAI_SOP_MERGE_SYNC_ENABLED`
