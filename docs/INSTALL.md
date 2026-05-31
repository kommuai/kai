# Installation

Shadou separates **engine** (this repo) from **tenant content** (`SHADOU_HOME`, default `~/.shadou/`).

## Quick install (local)

```bash
curl -fsSL https://raw.githubusercontent.com/YOUR_ORG/shadou/main/scripts/install.sh | bash
```

Or from a checkout:

```bash
./scripts/install.sh
export PATH="$HOME/.local/bin:$PATH"
export SHADOU_HOME=~/.shadou
```

## Bootstrap workspace

```bash
shadou workspace init                    # scaffold ~/.shadou from generic template
shadou pack install /path/to/tenant-pack # e.g. shadou-tenant-kommu repo
shadou doctor
shadou compile
```

## Docker (engine-only image)

Tenant content is **not** baked into the image. Mount `SHADOU_HOME`:

```bash
export SHADOU_HOME=~/.shadou
docker compose up -d --build
```

The entrypoint compiles FAQ if `compiled/kb_chunks.jsonl` is missing, then starts uvicorn on port 8000 (mapped to 6090 in compose).

## `SHADOU_HOME` layout

```
~/.shadou/
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
| `SHADOU_HOME` | `~/.shadou` | Tenant workspace root |
| `SHADOU_ENV_FILE` | `$SHADOU_HOME/.env` | Secrets |
| `SESSION_DB_PATH` | `$SHADOU_HOME/data/sessions.db` | SQLite sessions |
| `AGENT_WORKSPACE` | *(deprecated)* | Alias for `SHADOU_HOME` |

## Validation

```bash
shadou doctor
pytest tests/ --ignore=tests/test_support_runtime.py -q
```
