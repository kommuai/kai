# Kai — agent harness for support bots

Production-grade **engine** for workspace-driven support agents. Business content (FAQ, tools, copy) lives in **`KAI_HOME`** (default `~/.kai/`), not in this repo.

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

Docker:

```bash
export KAI_HOME=~/.kai
docker compose up -d --build
```

## Architecture

| Layer | Location |
|-------|----------|
| Engine (this repo) | `kai/` Python package, CLI, Docker image |
| Tenant workspace | `KAI_HOME` — `workspace.yaml`, FAQ, plugins |
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

- [docs/INSTALL.md](docs/INSTALL.md) — install, Docker, `KAI_HOME` layout
- [docs/OPERATOR.md](docs/OPERATOR.md) — day-to-day tenant edits
- [docs/PORTING.md](docs/PORTING.md) — author a tenant pack
- [docs/architecture/current_architecture_map.md](docs/architecture/current_architecture_map.md) — runtime flow

## Development

```bash
export KAI_HOME=tests/fixtures/kommu_workspace
pip install -r requirements.txt
pytest tests/ --ignore=tests/test_support_runtime.py -q
python3 tools/kai doctor --skip-compile
```

## Reference tenant

Kommu content lives in **`kai-tenant-kommu`** (sibling repo). Test fixture copy: `tests/fixtures/kommu_workspace/`.

Generic scaffold: `templates/workspace/generic/`.
