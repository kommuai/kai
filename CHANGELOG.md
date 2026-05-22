# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- `.env.example` and `secrets/README.md` documenting warranty Google Sheets credentials.
- `CHANGELOG.md` and workspace Cursor rule requiring changelog updates when agents change the repo.
- `core/outbound_delivery.py` — condense replies for Twilio WhatsApp 4096-char limit.

### Fixed

- **Docker build:** raise pip download timeout/retries so large wheels (e.g. `torch` via `sentence-transformers`) do not fail with `Read timed out`.
- **Docker Compose:** mount `./secrets` read-only so `GOOGLE_SHEETS_CREDENTIALS_JSON` file paths work in the container.
- **Warranty loader:** log when the credentials env points at a missing JSON file path (not only “missing/invalid”).
- **Clarify intent:** word-boundary matching so `installer` does not match `install` menu.
- **WhatsApp delivery:** cap outbound body length before Twilio send.

### Changed

- **v2-only HTTP surface:** removed `api/v1`; `POST /agent/message`, `POST /admin/*`, and `POST /v2/agent/message` are registered from [`api/v2/agent_message.py`](api/v2/agent_message.py).
- **Chat pipeline:** `pre_router` → `SupportRuntimeService.execute` only (FAQ-first + ReAct loop); `KAI_ROUTE_MODE` is a trace label.
- **LLM default:** `deepseek-v4-flash` via `KAI_LLM_MODEL` / `DEEPSEEK_MODEL`.
- **Language:** message routes use `is_malay()` for BM/EN consistently.
- **Docs:** `README.md`, `AGENTS.md`, `docs/architecture/*` aligned with current runtime.
- `tests/test_pre_router.py` — exercises `pre_router` and support runtime continuation.
- `services/kai_service.py` — slim module: session gates, footers, outbound prep, admin reset.

### Removed

- [`api/v1/agent_message.py`](api/v1/agent_message.py) (superseded by v2 router).
- `archive_legacy/`, `ARCHIVE_LEGACY.md`, `templates.py`, `workers/skill_worker.py`.
- Legacy chat paths: `KaiService.main_conversation`, `run_rag_dual`, `handle_agent_message`.
- `support_runtime/router.py`, `support_runtime/tools.py`, `support_runtime/warranty.py`.
- Unused workspace skill handlers under `agent_workspace/03_skills/*/handler.py`.
- `build_rag_system_prompt()` from `core/prompt_loader.py`.
- `tests/test_intent_accuracy.py` (IntentRouter); router tests folded into compiler/support-runtime tests.
