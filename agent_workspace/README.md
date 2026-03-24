# agent_workspace

This directory is the **content root** for Kai. Set `AGENT_WORKSPACE` to an absolute or app-relative path (default: `agent_workspace` next to `app.py`).

## Session database (SQLite)

Live sessions are **not** stored here. They live in SQLite:

| Environment | Typical path |
|-------------|----------------|
| Local default | `data/sessions.db` (relative to app root) |
| Docker | `/data/sessions.db` with host `./data` → `/data` |

See `SESSION_DB_PATH` and `DB_PATH` in `.env` / `docker-compose.yml`, and the `session_store` block in [`00_manifest.md`](00_manifest.md).

## Parity validation

After changes, run `pytest`, `docker compose up --build`, and hit `/`, `/agent/message`, `/v2/agent/message`, `/admin/refresh-sop`, `/admin/reset_memory` as described in the workspace rearchitecture plan.
