# Agent source policy (immutable)

The ReAct support brain uses **three tenant-owned layers**. Keep each in its lane:

| Layer | File | Job (layman) |
|-------|------|----------------|
| **Wiring** | `workspace.yaml` | What exists, when, how — channels, tools, hours, handover, copy strings |
| **Brain rules** | `system_prompt.md` | How to think and act — personality, MUST-call tools, JSON format |
| **Truth** | `knowledge/master_faq.md` | What is true — prices, policies, links, answers (via `search_faq` or full inject) |

Runtime assembly (`agent_context.build_agent_system_prompt`):

| Source | Mechanism |
|--------|-----------|
| Workspace settings | `workspace.yaml` → timezone, tenant id, inject mode |
| System prompt | `system_prompt.md` (full file) |
| Master FAQ | compiled chunks + `search_faq`; or full inject when `inject_mode: full_context` |
| Skills / tools | `tools_profile` → registry schemas + tool results |
| Session clock | Derived from workspace timezone |

**Not allowed** in `system_prompt.md`: product prices, policies, install links, or other facts that belong in master_faq.  
**Not allowed** in `workspace.yaml`: long agent instructions or FAQ answers.  
**Not allowed** anywhere in the brain prompt: `learnt_faq.md`, document `skills/*.md`, env secrets.

Implementation: `shadou/support_runtime/agent_context.py`  
Enforcement: `assert_prompt_sources_only()` at runtime startup; tests in `tests/test_agent_source_policy.py`.

## Tool determinism

Plugins under `tools/plugins/<id>/main.py` must:

1. Use `argparse` CLI flags.
2. Emit a single JSON object on stdout with `"ok": true|false`.
3. On failure, set `"error": "<exact reason>"` (never silent failure).

Validated by `shadou/tools_plugins/contract.py` on workspace validate and Studio AI Assist apply.

## Tenant-owned tool behavior

- **Tool ids** and legacy aliases live in tenant `workspace.yaml` → `tools_profile.tool_aliases`.
- **Plugins** stay under `SHADOU_HOME/tools/plugins/`; profile lists tenant-facing ids (e.g. `search_kommu_support`).
- **Grounded tools** (skip unverified footnote when tool succeeds): `agent.grounded_tools` in `workspace.yaml`.
- **Canonical builtins** are defined only in `shadou/support_runtime/tools/catalog.py` (platform repo).

The repo-root `agent_workspace/` tree is removed; production uses `SHADOU_HOME` (e.g. `shadou-tenant-kommu` or `~/.shadou`).

## Unified entry

All channels should call `shadou/support_runtime/gateway.run_support_turn()` so handover, grounding, and runtime behavior match WhatsApp and HTTP.
