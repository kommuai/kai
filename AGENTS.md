# AGENTS Guide

## Architecture boundaries

- `kai/api/v2/`: HTTP chat and admin routes (`POST /agent/message`, `/admin/*`, `/v2/agent/query`).
- `kai/services/kai_service.py`: `pre_router`, outbound footers, WhatsApp length limits.
- `kai/support_runtime/`: FAQ compiler, ReAct agent loop, clarify fallbacks.
- `agent_workspace/02_knowledge/faq/`: canonical FAQ source (`master_faq.md` → `compiled/`).
- `kai/core/`: SOP sync, FAQ markdown parser, outbound delivery.
- `kai/lib/`: session SQLite, DeepSeek client, Google Sheets warranty.

## Safe edit zones

- FAQ content: `agent_workspace/02_knowledge/faq/master_faq.md` then `/admin/refresh-sop`.
- Agent behavior: `kai/support_runtime/agent_prompts.py`, `kai/support_runtime/agent_tools.py`.
- Full FAQ in system prompt: `kai/support_runtime/faq_context.py`; session chat via `SESSION_IDLE_HOURS` (default 24h) in `kai/lib/session_state.py`.
- Clarify format rules: `kai/support_runtime/clarify_validation.py` (hedge repair when the model chooses `clarifying_question`).

## Restricted edits

- Do not break `POST /agent/message` payload/response envelope (n8n/WhatsApp).
- Keep `pre_router` before `support_runtime_service.execute`.
- Do not reintroduce removed legacy paths (`main_conversation`, `archive_legacy`, `IntentRouter`).

## Verification

```bash
pytest tests/test_architecture_import_boundaries.py tests/test_agent_loop.py tests/test_api_contracts.py -q
```
