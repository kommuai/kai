# Current architecture map

Production chat flow (WhatsApp / n8n):

```
POST /agent/message  (or /v2/agent/message)
  → ShadouService.pre_router          # handover, frozen, session priming
  → SupportRuntimeService.execute  # FAQ-first + ReAct agent loop
  → ShadouService.finalize_reply        # outbound_delivery WhatsApp 4096 cap
```

## Operator edit surface

See [`docs/OPERATOR.md`](../OPERATOR.md): files under `SHADOU_HOME` (`~/.shadou/` by default).

## Active packages

| Path | Role |
|------|------|
| `app.py` | FastAPI ASGI entry |
| `shadou/api/v2/` | Chat + admin + agent query routes |
| `shadou/content/` | Prompts, FAQ cache, copy/channels from `workspace.yaml` |
| `shadou/settings/` | `SHADOU_HOME`, env, paths |
| `shadou/services/shadou_service.py` | `pre_router`, footers |
| `shadou/support_runtime/` | Compiler, ReAct loop, tools |
| `shadou/lib/session_state.py` | SQLite sessions + memory facts |
| `shadou/core/outbound_delivery.py` | WhatsApp length cap |

Tenant content is **not** in the engine repo — install via `shadou pack install` into `SHADOU_HOME`.

## Knowledge refresh

- `POST /admin/refresh-sop` → compile FAQ + reload caches
- Optional daily SOP merge: `SHADOU_SOP_MERGE_SYNC_ENABLED` → `SHADOU_HOME/data/sop/sop_sync_state.json`

## Removed legacy

- IntentRouter / workspace skill handlers / numbered `03_tools/` layout
- Repo-root `agent_workspace/` (use `SHADOU_HOME` + tenant packs)
- Split `requirements-dev.txt` / `requirements-optional.txt` (merged into `requirements.txt`)
