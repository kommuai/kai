# Kai — Agent context

## 2026-05-23 — Requirements merge + doc/media cleanup

- **requirements.txt:** merged runtime, integrations, and dev/CI deps; removed `requirements-dev.txt` and `requirements-optional.txt`.
- **media/:** removed repo-root folder; cache path is now `KAI_HOME/data/media` (optional WhatsApp download; not on default chat route).
- **Docs removed:** `docs/SETUP.md`, stale `docs/architecture/*` (workspace_v2, routing, skills, policies, contexts, hermes phases).
- **Validation:** pytest 120 passed.

## 2026-05-23 — Production harness refactor (~/.kai/)

- **Intent:** Hermes-style split — engine repo vs `KAI_HOME` tenant workspace; Kommu moved to `kai-tenant-kommu` repo.
- **Added:** `kai/settings/paths.py`, `kai/cli/pack.py`, `scripts/install.sh`, `scripts/docker-entrypoint.sh`, `tests/fixtures/{minimal,kommu}_workspace`, `docs/INSTALL.md`.
- **CLI:** `kai workspace init`, `kai pack install|export`; `KAI_HOME` replaces `AGENT_WORKSPACE` (deprecated shim).
- **Removed from engine repo:** `agent_workspace/`, `packs/`, `x`, `kai/integrations/`, legacy numbered-path fallbacks.
- **Validation:** pytest 120 passed; doctor OK on kommu fixture; init+pack install smoke on `/tmp/kai-home-test`.

## 2026-05-22 — Full E2E validation (20 live questions)

- **Results:** 20/20 live Q&A HTTP 200 via `POST /v2/agent/message`.
