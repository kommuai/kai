# Installation

Kai separates **engine** (this repo) from **tenant content** (`KAI_HOME`, default `~/.kai/`).

## Quick install (local)

```bash
curl -fsSL https://raw.githubusercontent.com/YOUR_ORG/kai/main/scripts/install.sh | bash
```

Or from a checkout:

```bash
./scripts/install.sh
export PATH="$HOME/.local/bin:$PATH"
export KAI_HOME=~/.kai
```

## Bootstrap workspace

```bash
kai workspace init                    # scaffold ~/.kai from generic template
kai pack install /path/to/tenant-pack # e.g. kai-tenant-kommu repo
kai doctor
kai compile
```

## Docker (engine-only image)

Tenant content is **not** baked into the image. Mount `KAI_HOME`:

```bash
export KAI_HOME=~/.kai
docker compose up -d --build
```

The entrypoint compiles FAQ if `compiled/kb_chunks.jsonl` is missing, then starts uvicorn on port 8000 (mapped to 6090 in compose).

## `KAI_HOME` layout

```
~/.kai/
├── workspace.yaml
├── system_prompt.md
├── .env
├── knowledge/master_faq.md
├── skills/
├── tools/plugins/
├── compiled/
└── data/sessions.db
```

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `KAI_HOME` | `~/.kai` | Tenant workspace root |
| `KAI_ENV_FILE` | `$KAI_HOME/.env` | Secrets |
| `SESSION_DB_PATH` | `$KAI_HOME/data/sessions.db` | SQLite sessions |
| `AGENT_WORKSPACE` | *(deprecated)* | Alias for `KAI_HOME` |

## Validation

```bash
kai doctor
pytest tests/ --ignore=tests/test_support_runtime.py -q
```
