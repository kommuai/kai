# Agent source policy (immutable)

The ReAct support brain may use **only** these context sources:

| Source | File / mechanism |
|--------|------------------|
| Workspace settings | `workspace.yaml` → injected via `agent_context.workspace_settings_block()` |
| System prompt | `system_prompt.md` |
| Master FAQ | `knowledge/master_faq.md` (full inject or `search_faq` compiled from it) |
| Skills / tools | `tools_profile` → registry schemas + tool results |
| Session clock | Derived from workspace timezone (scheduling only) |

**Not allowed** in the system prompt: `learnt_faq.md`, document `skills/*.md`, raw SOP Google Doc text, env secrets, or ad-hoc hardcoded product copy.

Implementation: `kai/support_runtime/agent_context.py`  
Enforcement: `assert_prompt_sources_only()` at runtime startup; tests in `tests/test_agent_source_policy.py`.

## Tool determinism

Plugins under `tools/plugins/<id>/main.py` must:

1. Use `argparse` CLI flags.
2. Emit a single JSON object on stdout with `"ok": true|false`.
3. On failure, set `"error": "<exact reason>"` (never silent failure).

Validated by `kai/tools_plugins/contract.py` on workspace validate and Studio AI Assist apply.

## Unified entry

All channels should call `kai/support_runtime/gateway.run_support_turn()` so handover, grounding, and runtime behavior match WhatsApp and HTTP.
