# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- `tools/clear_chat.py` — CLI to clear session/history for a phone number (`python tools/clear_chat.py 0173611088`).

### Changed

- **FAQ (`master_faq.md`):** added `regional_installer` and `regional_installer_followup` intents (Penang/outstation partner installers, aliases for "one in penang"); narrowed `install_booking` to HQ appointments; clarified `self_install` vs partner vs HQ.
- **Clarify fallback:** if the ReAct path still lacks grounding, `installer` queries no longer fall through to the generic HQ/self-install menu (word-boundary only; not a routing change).

### Added

- `kai/` Python package: consolidated `api`, `core`, `support_runtime`, `services`, `integrations`, `rag`, and shared `lib/` modules.
- `pytest.ini` — `pythonpath = .` for tests after package layout change.
- `kai/core/outbound_delivery.py` — WhatsApp 4096-char safe replies.

### Changed

- **Repo layout:** application code lives under `kai/`; root keeps `app.py`, `config.py`, `.env`, Docker, and runtime data dirs (`agent_workspace`, `data`, `logs`, `media`, `secrets`).
- `config.SOP_SYNC_STATE_PATH` → `data/sop/sop_sync_state.json` (moved out of removed `kai/rag/`).
- `debug_check.py` → `tools/debug_check.py`; `AGENT_CONTEXT.md` → `docs/AGENT_CONTEXT.md`.
- All Python imports updated to `kai.*` namespace.
- `.env.example` and `secrets/README.md` documenting warranty Google Sheets credentials (when present).

### Fixed

- **Docker build:** raise pip download timeout/retries so large wheels (e.g. `torch` via `sentence-transformers`) do not fail with `Read timed out`.
- **Docker Compose:** mount `./secrets` read-only so `GOOGLE_SHEETS_CREDENTIALS_JSON` file paths work in the container.
- **Warranty loader:** log when the credentials env points at a missing JSON file path (not only “missing/invalid”).
- **Clarify intent:** word-boundary matching so `installer` does not match `install` menu.
- **WhatsApp delivery:** cap outbound body length before Twilio send.

### Changed

- **v2-only HTTP surface:** removed `api/v1`; `POST /agent/message`, `POST /admin/*`, and `POST /v2/agent/message` are registered from [`kai/api/v2/agent_message.py`](kai/api/v2/agent_message.py).
- **Chat pipeline:** `pre_router` → `SupportRuntimeService.execute` only (FAQ-first + ReAct loop); `KAI_ROUTE_MODE` is a trace label.
- **LLM default:** `deepseek-v4-flash` via `KAI_LLM_MODEL` / `DEEPSEEK_MODEL`.
- **Language:** message routes use `is_malay()` for BM/EN consistently.
- **Docs:** `README.md`, `AGENTS.md`, `docs/architecture/*` aligned with current runtime.
- `tests/test_pre_router.py` — exercises `pre_router` and support runtime continuation.
- `kai/services/kai_service.py` — slim module: session gates, footers, outbound prep, admin reset.

### Removed

- **Legacy FAISS RAG:** `kai/rag/` (`RAGEngine`, `build_index.py`, `sop_data.json`, test fixtures); `faiss-cpu`, `sentence-transformers`, `fastembed`, `onnxruntime` from `requirements.txt`.
- `kai/core/sop_ingest.py` (unused; FAQ ingest is `master_faq.md` + `compile_canonical_knowledge()`).
- [`api/v1/agent_message.py`](api/v1/agent_message.py) (superseded by v2 router).
- `archive_legacy/`, `ARCHIVE_LEGACY.md`, `templates.py`, `workers/skill_worker.py`.
- Legacy chat paths: `KaiService.main_conversation`, `run_rag_dual`, `handle_agent_message`.
- `support_runtime/router.py`, `support_runtime/tools.py`, `support_runtime/warranty.py`.
- Unused workspace skill handlers under `agent_workspace/03_skills/*/handler.py`.
- `build_rag_system_prompt()` from `core/prompt_loader.py`.
- `tests/test_intent_accuracy.py` (IntentRouter); router tests folded into compiler/support-runtime tests.
