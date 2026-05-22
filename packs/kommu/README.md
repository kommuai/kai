# Kommu tenant pack

This repository ships the Kommu workspace at **`agent_workspace/`** (repo root). That directory is the live tenant pack — not a copy under `packs/`.

## Porting another business

1. Fork or clone the engine repo.
2. Replace `agent_workspace/` with output from `python3 tools/kai init`, or keep Kommu as reference and edit in place.
3. Use the **generic** tool profile in `templates/workspace/generic/03_tools/tools.yaml` as a minimal starting point.

See [docs/PORTING.md](../../docs/PORTING.md) and [docs/SETUP.md](../../docs/SETUP.md).

## Kommu-specific env (examples)

- `WARRANTY_CSV_URL`, `EXTRA_WARRANTY_CSV_URL` — sheet lookups
- `KAI_GITHUB_REPO` / `BUKAPILOT_REPO` — backlog search (overridable in `tools.yaml`)
- `SMARTSERVA_USERNAME`, `SMARTSERVA_PASSWORD` — visitor pass plugin
- `KAI_SOP_MERGE_SYNC_ENABLED=1` — optional daily SOP merge (off for new tenants)
