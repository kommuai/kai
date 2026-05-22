# Current architecture map

Production chat flow (WhatsApp / n8n):

```
POST /agent/message  (or /v2/agent/message)
  → KaiService.pre_router          # handover, frozen, session priming
  → SupportRuntimeService.execute  # FAQ-first + ReAct agent loop
  → KaiService.finalize_reply        # outbound_delivery WhatsApp 4096 cap
```

## Operator edit surface

See [`docs/OPERATOR.md`](../OPERATOR.md): `01_core/system_prompt.md`, `02_knowledge/faq/master_faq.md`, `05_copy/chat_copy.yaml`, `.env`.

## Active packages

| Path | Role |
|------|------|
| `app.py` | FastAPI app, startup refresh, optional SOP merge cron |
| `kai/api/v2/` | Chat + admin + agent query routes |
| `kai/content/` | Loads prompts, FAQ cache, chat copy from `agent_workspace/` |
| `kai/settings/` | Central env configuration (`config.py` re-exports) |
| `kai/services/kai_service.py` | `pre_router`, footers; `turn_ingest.py` for session writes |
| `kai/support_runtime/` | Compiler, ReAct loop, agent tools |
| `agent_workspace/` | FAQ markdown → `compiled/kb_chunks.jsonl` |
| `kai/lib/session_state.py` | SQLite sessions + memory facts |
| `kai/core/outbound_delivery.py` | WhatsApp length cap (`prepare_outbound_reply`) |

## Removed (legacy cleanup)

- Top-level shells (`api/`, `core/`, `services/`, `support_runtime/`, `rag/`, `integrations/`) — empty `__pycache__` only; runtime lives under `kai/`
- `archive_legacy/` — old RouterEngine + workspace skill loaders
- `KaiService.main_conversation` / `run_rag_dual` / `handle_agent_message`
- `support_runtime/router.py` (IntentRouter) — routing is FAQ-first + ReAct agent loop
- `support_runtime/tools.py` (ToolPolicyEngine) — unused in ReAct path
- `support_runtime/warranty.py` — warranty via `agent_tools.lookup_warranty`
- `templates.py`, `workers/skill_worker.py`
- Unused `agent_workspace/03_skills/*/handler.py` skill stubs

## Knowledge refresh

- `POST /admin/refresh-sop` → `compile_canonical_knowledge()` + warranty sheet load
- Optional daily SOP merge: `KAI_SOP_MERGE_SYNC_ENABLED` (state file: `data/sop/sop_sync_state.json`)

## Removed legacy RAG

- FAISS / `RAGEngine` / `run_rag_dual` — not used in production. Retrieval is FAQ compiler + `HybridRetriever` (Qdrant or local `kb_chunks.jsonl`).
- `docs/architecture/turn_orchestrator.md` — unimplemented design proposal (removed).
