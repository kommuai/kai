# Current Architecture Map

This map shows the active runtime and the archived legacy areas.

## Active Runtime (Keep)

- API entrypoints:
  - `api/v2/agent_message.py`
  - `api/v2/agent_query.py`
- Runtime pipeline:
  - `support_runtime/`
    - `service.py`
    - `agent_loop.py`
    - `agent_tools.py`
    - `agent_prompts.py`
    - `retrieval.py`
    - `compiler.py`
    - `providers.py`
    - `guardrails.py`
    - `observability.py`
- Chatwoot parity/session behavior:
  - `services/kai_service.py`
  - `session_state.py`
- App bootstrap:
  - `app.py`
  - `config.py`
- Operational note:
  - Startup and scheduled refresh are owned by `support_runtime_service`.
  - Legacy v2 shadow execution path has been removed.

## Active Knowledge + Evaluation

- Canonical source:
  - `agent_workspace/02_knowledge/faq/master_faq.md`
- Compiled runtime artifacts:
  - `agent_workspace/compiled/`
- Eval and quality checks:
  - `tools/eval_support_runtime.py`
  - `tests/test_pre_router.py`
  - `tests/test_chatwoot_parity_contract.py`
  - `tests/test_support_runtime.py`

## Archived Legacy (Moved)

- `archive_legacy/docs/legacy_tool_paths.md`
- `archive_legacy/core_router/engine.py`
- `archive_legacy/skills_runtime/workspace_factory.py`
- `archive_legacy/skills_runtime/workspace_registry.py`
- `archive_legacy/skills_runtime/legacy_rag/`
- `archive_legacy/skills_runtime/legacy_warranty/`

These legacy files are kept for reference/rollback and are not part of the current runtime flow.

## Removed During Refactor (No Longer Used)

- `core/policy/tool_adapter.py`
- `core/skills/registry.py`
- `tools/check_architecture.py`
- `support_runtime/graph.py`
- `support_runtime/vehicle_support.py`
- `support_runtime/agentic_understanding.py`

