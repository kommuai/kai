# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- `.env.example` and `secrets/README.md` documenting warranty Google Sheets credentials.
- `CHANGELOG.md` and workspace Cursor rule requiring changelog updates when agents change the repo.

### Fixed

- **Docker build:** raise pip download timeout/retries so large wheels (e.g. `torch` via `sentence-transformers`) do not fail with `Read timed out`.
- **Docker Compose:** mount `./secrets` read-only so `GOOGLE_SHEETS_CREDENTIALS_JSON` file paths work in the container.
- **Warranty loader:** log when the credentials env points at a missing JSON file path (not only “missing/invalid”).
- `tests/test_pre_router.py` — parity checks for `pre_router` / `main_conversation` vs `handle_agent_message`.

### Changed

- **v2-only HTTP surface:** removed `api/v1`; `POST /agent/message`, `POST /admin/*`, and `POST /v2/agent/message` are registered from [`api/v2/agent_message.py`](api/v2/agent_message.py).
- **Chat pipeline:** `KaiService.pre_router` (handover, frozen, user turn) runs before `RouterEngine`; fallback uses `main_conversation` only (fixes duplicate user history on skill miss).
- **Language:** message routes use `is_malay()` for BM/EN consistently.
- **Route mode:** default `KAI_ROUTE_MODE` is `hybrid`; `stable_only` env maps to `hybrid`; removed `RouteMode.STABLE_ONLY` and router “first skill only” behavior.

### Removed

- [`api/v1/agent_message.py`](api/v1/agent_message.py) (superseded by v2 router).
