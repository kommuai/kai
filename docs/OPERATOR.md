# Operator guide

All tenant edits happen under **`KAI_HOME`** (default `~/.kai/`).

## What to edit

| What | Path under `KAI_HOME` |
|------|------------------------|
| Tenant config (channels, copy, tools) | `workspace.yaml` |
| Bot instructions | `system_prompt.md` |
| FAQ | `knowledge/master_faq.md` |
| Tool plugins | `tools/plugins/<id>/main.py` |
| Optional skills docs | `skills/` |
| Secrets | `.env` |

## After edits

```bash
kai compile
curl -X POST http://127.0.0.1:6090/admin/refresh-sop -H "x-admin-token: $ADMIN_TOKEN"
# or
kai doctor
```

## Learn queue

Post-handover FAQ proposals: `knowledge/learn_queue/<proposal_id>/`

## Chatwoot (direct Agent Bot)

Production can use Chatwoot Agent Bot → Kai `/webhooks/chatwoot` instead of n8n. See [CHATWOOT.md](CHATWOOT.md) for env vars and cutover steps.

## Install / porting

See [INSTALL.md](INSTALL.md) and [PORTING.md](PORTING.md).
