# Shadou — agent harness for support bots

Production-grade **engine** for workspace-driven support agents. Business content (FAQ, tools, copy) lives in **`SHADOU_HOME`** (default `~/.shadou/`), not in this repo.

This repository is a **monorepo**:

| Path | Role |
|------|------|
| `shadou/` | Python engine package, CLI, tests |
| `app.py`, `docker-compose.yml` | Runtime HTTP service (engine) |
| `studio/` | **Shadou Studio** — admin UI (FastAPI + React), own Docker compose |

Hermes-style layout: install engine → `shadou workspace init` → `shadou pack install <tenant>` → run.

## Quick start

```bash
./scripts/install.sh
export PATH="$HOME/.local/bin:$PATH"
export SHADOU_HOME=~/.shadou

shadou workspace init
shadou pack install /path/to/shadou-tenant-kommu   # separate tenant repo
shadou doctor
uvicorn app:app --host 127.0.0.1 --port 6090
```

Docker (engine only):

```bash
export SHADOU_HOME=~/.shadou
docker compose up -d --build
```

Shadou Studio (separate stack):

```bash
cd studio && cp backend/.env.example backend/.env
docker compose up -d --build
# UI http://localhost:5173  API http://localhost:8080
```

Dev without Docker: `./studio/start.sh` — see [studio/README.md](studio/README.md) and [docs/STUDIO.md](docs/STUDIO.md).

## Architecture

| Layer | Location |
|-------|----------|
| Engine (this repo) | `shadou/` Python package, CLI, root Docker image |
| Shadou Studio | `studio/` — tenant editor, inbox, contacts |
| Tenant workspace | `SHADOU_HOME` or `shadou-tenant-*` under `SHADOU_TENANTS_ROOT` |
| Tenant packs | Separate repos/tarballs installed via `shadou pack install` |

Chat path: `POST /v2/agent/message` → pre-router → ReAct runtime → finalize reply.

## CLI

| Command | Purpose |
|---------|---------|
| `shadou workspace init` | Scaffold empty `~/.shadou` |
| `shadou pack install <src>` | Apply tenant pack (dir or `.tar.gz`) |
| `shadou pack export` | Export tenant workspace |
| `shadou doctor` | Validate layout, tools, FAQ |
| `shadou compile` | Build `compiled/kb_chunks.jsonl` |

## Docs

- [docs/STUDIO.md](docs/STUDIO.md) — Shadou Studio, OAuth, Studio Docker
- [docs/INSTALL.md](docs/INSTALL.md) — install, Docker, `SHADOU_HOME` layout
- [docs/OPERATOR.md](docs/OPERATOR.md) — day-to-day tenant edits
- [docs/PORTING.md](docs/PORTING.md) — author a tenant pack
- [docs/architecture/current_architecture_map.md](docs/architecture/current_architecture_map.md) — runtime flow

## Development

```bash
export SHADOU_HOME=tests/fixtures/minimal_workspace
pip install -r requirements.txt
pytest tests/ --ignore=tests/test_support_runtime.py -q
python3 tools/shadou doctor --skip-compile
```

## Reference tenant

Kommu content lives in **`shadou-tenant-kommu`** (sibling repo). Run tenant-specific tests there with `SHADOU_HOME` pointing at that pack.

Generic scaffold: `templates/workspace/generic/`.
