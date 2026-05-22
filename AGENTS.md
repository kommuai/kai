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
- Clarify fallbacks: `kai/support_runtime/clarify_intent.py`, `kai/support_runtime/clarify_validation.py`.

## Restricted edits

- Do not break `POST /agent/message` payload/response envelope (n8n/WhatsApp).
- Keep `pre_router` before `support_runtime_service.execute`.
- Do not reintroduce removed legacy paths (`main_conversation`, `archive_legacy`, `IntentRouter`).

## Verification

```bash
pytest tests/test_architecture_import_boundaries.py tests/test_clarify_intent.py tests/test_api_contracts.py -q
```
