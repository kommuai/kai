# Current architecture map

Production chat flow (WhatsApp / n8n):

```
POST /agent/message  (or /v2/agent/message)
  → KaiService.pre_router          # handover, frozen, session priming
  → SupportRuntimeService.execute  # FAQ-first + ReAct agent loop
  → KaiService.finalize_reply        # outbound_delivery WhatsApp 4096 cap
```

## Operator edit surface

See [`docs/OPERATOR.md`](../OPERATOR.md): files under `KAI_HOME` (`~/.kai/` by default).

## Active packages

| Path | Role |
|------|------|
| `app.py` | FastAPI ASGI entry |
| `kai/api/v2/` | Chat + admin + agent query routes |
| `kai/content/` | Prompts, FAQ cache, copy/channels from `workspace.yaml` |
| `kai/settings/` | `KAI_HOME`, env, paths |
| `kai/services/kai_service.py` | `pre_router`, footers |
| `kai/support_runtime/` | Compiler, ReAct loop, tools |
| `kai/lib/session_state.py` | SQLite sessions + memory facts |
| `kai/core/outbound_delivery.py` | WhatsApp length cap |

Tenant content is **not** in the engine repo — install via `kai pack install` into `KAI_HOME`.

## Knowledge refresh

- `POST /admin/refresh-sop` → compile FAQ + reload caches
- Optional daily SOP merge: `KAI_SOP_MERGE_SYNC_ENABLED` → `KAI_HOME/data/sop/sop_sync_state.json`

## Removed legacy

- IntentRouter / workspace skill handlers / numbered `03_tools/` layout
- Repo-root `agent_workspace/` (use `KAI_HOME` + tenant packs)
- Split `requirements-dev.txt` / `requirements-optional.txt` (merged into `requirements.txt`)
