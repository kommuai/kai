# Operator guide

All tenant edits happen under **`SHADOU_HOME`** (default `~/.shadou/`).

## What to edit

| What | Path under `SHADOU_HOME` |
|------|------------------------|
| Tenant config (channels, copy, tools) | `workspace.yaml` |
| AI support agent instructions | `system_prompt.md` |
| FAQ | `knowledge/master_faq.md` |
| Tool plugins | `tools/plugins/<id>/main.py` |
| Optional skills docs | `skills/` |
| Secrets | `.env` |

## After edits

```bash
shadou compile
curl -X POST http://127.0.0.1:6090/admin/refresh-sop -H "x-admin-token: $ADMIN_TOKEN"
# or
shadou doctor
```

## Admin mode and deliberate FAQ learning

Admins (numbers listed in `workspace.yaml` under `admin.whitelist_numbers`) have special WhatsApp commands:

| Command | Effect |
|---------|--------|
| `/admin` | Enters admin mode: AI support agent is paused for that number; it will not respond to normal messages. |
| `/test` | Enters test/user mode: AI support agent is unpaused and responds normally (for testing the AI support agent as a user). |
| `/learning` | (Requires admin mode) Presents low-confidence user questions one at a time for review. |
| `/learning skip` | Skips the current question. |
| `/learning stop` | Ends the learning session. |

When an admin types a plain-text answer during a `/learning` session, a proposal is written to `knowledge/learn_queue/`.

### Configuring admins in `workspace.yaml`

```yaml
admin:
  whitelist_numbers:
    - "+60199999999"
  learning:
    enabled: true
    min_confidence: 0.6   # events below this confidence are queued
    max_items: 10         # max questions shown per /learning session
```

### Reviewing and applying proposals

```bash
python3 tools/merge_learn_queue.py --list
python3 tools/merge_learn_queue.py --apply <proposal_id> --compile
```

## Install / porting

See [INSTALL.md](INSTALL.md) and [PORTING.md](PORTING.md).
