# AGENTS Guide

## Architecture boundaries

- `api/v2/`: HTTP chat and admin routes (`POST /agent/message`, `/admin/*`, `/v2/agent/query`).
- `services/kai_service.py`: `pre_router`, outbound footers, WhatsApp length limits.
- `support_runtime/`: FAQ compiler, ReAct agent loop, turn planner, evidence policy.
- `agent_workspace/02_knowledge/faq/`: canonical FAQ source (`master_faq.md` → `compiled/`).
- `core/`: SOP sync, FAQ markdown parser, outbound delivery.

## Safe edit zones

- FAQ content: `agent_workspace/02_knowledge/faq/master_faq.md` then `/admin/refresh-sop`.
- Agent behavior: `support_runtime/agent_prompts.py`, `support_runtime/agent_tools.py`.
- Clarify fallbacks: `support_runtime/clarify_intent.py`, `support_runtime/clarify_validation.py`.

## Restricted edits

- Do not break `POST /agent/message` payload/response envelope (n8n/WhatsApp).
- Keep `pre_router` before `support_runtime_service.execute`.
- Do not reintroduce removed legacy paths (`main_conversation`, `archive_legacy`, `IntentRouter`).

## Verification

```bash
pytest tests/test_architecture_import_boundaries.py tests/test_clarify_intent.py tests/test_api_contracts.py -q
```
