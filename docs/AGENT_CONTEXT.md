# Shadou — Agent context

## 2026-05-23 — Requirements merge + doc/media cleanup

- **requirements.txt:** merged runtime, integrations, and dev/CI deps; removed `requirements-dev.txt` and `requirements-optional.txt`.
- **media/:** removed repo-root folder; cache path is now `SHADOU_HOME/data/media` (optional WhatsApp download; not on default chat route).
- **Docs removed:** `docs/SETUP.md`, stale `docs/architecture/*` (workspace_v2, routing, skills, policies, contexts, hermes phases).
- **Validation:** pytest 120 passed.

## 2026-05-23 — Production harness refactor (~/.shadou/)

- **Intent:** Hermes-style split — engine repo vs `SHADOU_HOME` tenant workspace; Kommu moved to `shadou-tenant-kommu` repo.
- **Added:** `shadou/settings/paths.py`, `shadou/cli/pack.py`, `scripts/install.sh`, `scripts/docker-entrypoint.sh`, `tests/fixtures/{minimal,kommu}_workspace`, `docs/INSTALL.md`.
- **CLI:** `shadou workspace init`, `shadou pack install|export`; `SHADOU_HOME` replaces `AGENT_WORKSPACE` (deprecated shim).
- **Removed from engine repo:** `agent_workspace/`, `packs/`, `x`, `shadou/integrations/`, legacy numbered-path fallbacks.
- **Validation:** pytest 120 passed; doctor OK on kommu fixture; init+pack install smoke on `/tmp/shadou-home-test`.

## 2026-05-22 — Full E2E validation (20 live questions)

- **Results:** 20/20 live Q&A HTTP 200 via `POST /v2/agent/message`.
