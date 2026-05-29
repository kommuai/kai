# Kai — agent harness for support bots

Production-grade **engine** for workspace-driven support agents. Business content (FAQ, tools, copy) lives in **`KAI_HOME`** (default `~/.kai/`), not in this repo.

This repository is a **monorepo**:

| Path | Role |
|------|------|
| `kai/` | Python engine package, CLI, tests |
| `app.py`, `docker-compose.yml` | Runtime HTTP service (engine) |
| `studio/` | **Kai Studio** — admin UI (FastAPI + React), own Docker compose |

Hermes-style layout: install engine → `kai workspace init` → `kai pack install <tenant>` → run.

## Quick start

```bash
./scripts/install.sh
export PATH="$HOME/.local/bin:$PATH"
export KAI_HOME=~/.kai

kai workspace init
kai pack install /path/to/kai-tenant-kommu   # separate tenant repo
kai doctor
uvicorn app:app --host 127.0.0.1 --port 6090
```

Docker (engine only):

```bash
export KAI_HOME=~/.kai
docker compose up -d --build
```

Kai Studio (separate stack):

```bash
cd studio && cp backend/.env.example backend/.env
docker compose up -d --build
# UI http://localhost:5173  API http://localhost:8080
```

Dev without Docker: `./studio/start.sh` — see [studio/README.md](studio/README.md) and [docs/STUDIO.md](docs/STUDIO.md).

## Architecture

| Layer | Location |
|-------|----------|
| Engine (this repo) | `kai/` Python package, CLI, root Docker image |
| Kai Studio | `studio/` — tenant editor, inbox, contacts |
| Tenant workspace | `KAI_HOME` or `kai-tenant-*` under `KAI_TENANTS_ROOT` |
| Tenant packs | Separate repos/tarballs installed via `kai pack install` |

Chat path: `POST /v2/agent/message` → pre-router → ReAct runtime → finalize reply.

## CLI

| Command | Purpose |
|---------|---------|
| `kai workspace init` | Scaffold empty `~/.kai` |
| `kai pack install <src>` | Apply tenant pack (dir or `.tar.gz`) |
| `kai pack export` | Export tenant workspace |
| `kai doctor` | Validate layout, tools, FAQ |
| `kai compile` | Build `compiled/kb_chunks.jsonl` |

## Docs

- [docs/STUDIO.md](docs/STUDIO.md) — Kai Studio, OAuth, Studio Docker
- [docs/INSTALL.md](docs/INSTALL.md) — install, Docker, `KAI_HOME` layout
- [docs/OPERATOR.md](docs/OPERATOR.md) — day-to-day tenant edits
- [docs/PORTING.md](docs/PORTING.md) — author a tenant pack
- [docs/architecture/current_architecture_map.md](docs/architecture/current_architecture_map.md) — runtime flow

## Development

```bash
export KAI_HOME=tests/fixtures/minimal_workspace
pip install -r requirements.txt
pytest tests/ --ignore=tests/test_support_runtime.py -q
python3 tools/kai doctor --skip-compile
```

## Reference tenant

Kommu content lives in **`kai-tenant-kommu`** (sibling repo). Run tenant-specific tests there with `KAI_HOME` pointing at that pack.

Generic scaffold: `templates/workspace/generic/`.
