# Agent edit boundaries

## Engine (this repo)

| Area | Path |
|------|------|
| HTTP routes, ReAct loop, builtins | `shadou/` |
| CLI, installer, Docker | `shadou/cli/`, `scripts/` |
| Tests + fixtures | `tests/` |
| Generic template (stubs only) | `templates/workspace/generic/` |

## Tenant (never in engine repo)

| Area | Path under `SHADOU_HOME` |
|------|------------------------|
| Config | `workspace.yaml` |
| Prompt + FAQ | `system_prompt.md`, `knowledge/master_faq.md` |
| Plugins | `tools/plugins/` |

Do not add business-specific FAQ, prompts, or plugins to the engine repo. Use a tenant pack (`shadou pack install`).

## Stable chat path

`POST /v2/agent/message` → `pre_router` → `SupportRuntimeService.execute` → `finalize_reply`

Do not break the request/response envelope (n8n/WhatsApp integrators).
