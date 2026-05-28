# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- **Refactor migration:** merged `origin/refactor` (workspace v2 / `KAI_HOME`); `docker-compose.kommu.yml` for Kommu production; `docker-compose.staging.yml` + `migration/` scripts (baseline, validate, rollback).
- **Compat:** pre-router uses `freeze()` and handoff segments; n8n `message_type` media guard; `MASTER_FAQ_PATH` keeps legacy `agent_workspace/02_knowledge/faq/master_faq.md`.
- **Kommu tenant restore:** runtime now uses host `~/.kai` (`workspace.yaml` + `system_prompt.md`) mounted into `/kai-home` so refactor loads Kommu tone/rules and full tools profile (vehicle support, warranty, backlog, visitor pass).
- **Admin whitelist:** added `+60173611088` / `0173611088` to `workspace.yaml` `admin.whitelist_numbers` for `/admin` and `/learning` commands.
- **KAI_HOME migration:** moved runtime tenant state to host `~/.kai` and updated compose to mount `~/.kai:/kai-home` (includes `.env`, `workspace.yaml`, `system_prompt.md`, `knowledge/master_faq.md`, and `data/sessions.db`).

### Added

- **FAQ:** `international_shipping_regions`, `indonesia_market`, `lhd_rhd_steering` — stop invented "Malaysia only" / "no Indonesia" / "RHD-only" claims; route country and LHD questions to support@kommu.ai or LA.
- **`faq_grounding.py`:** on `direct_answer` without FAQ/tool evidence, append a short footnote that the detail is not in the official FAQ and will be reviewed by a live agent (type LA); skips generic greetings.

### Changed

- **Agent prompts:** require FAQ intents for international shipping and LHD/RHD; recommend `source_ids` with `faq:<intent_id>` on grounded replies.

### Added

- **Full FAQ context:** every agent turn injects complete `master_faq.md` into the system prompt (`faq_context.py`); session chat is the full message list for the active session (default **24h** idle timeout, up to **100** turns).
- `SESSION_IDLE_HOURS`, `SESSION_MAX_HISTORY_MESSAGES` config; `ensure_active_session()` resets history after idle window.
- `docs/architecture/turn_orchestrator.md` — proposed state-driven turn pipeline (ConversationState, PolicyRouter, CanonicalExecutor, workflow compiler metadata) to replace FAQ-hint + implicit ReAct routing.

### Removed

- Regex-based clarify routing (`clarify_intent.py` / `pick_clarify_for_intent`) and `MEMORY_DEPTH=10` cap on session chat (replaced by session window settings).

### Added

- `tools/clear_chat.py` — CLI to clear session/history for a phone number (`python tools/clear_chat.py 0173611088`).

### Changed

- **Agent prompts + FAQ:** answer-first rules (no default pricing/install upsell); new FAQ intents `vehicle_manufacturer_warranty`, `insurance_out_of_scope`; expanded `warranty` aliases; suppress LA footer on normal bot replies.
- **Live-agent auto-resume:** after `SESSION_IDLE_HOURS` (default 24h), `frozen` clears automatically with **no** outbound message; manual `resume` / `unfreeze` / `sambung` still sends the Bot resumed ack.
- **Pricing continuity:** FAQ `installation_fees`, `pricing_followup` — disambiguate install fees vs device price; prompts ban empty \"anything else I can help?\" when user still asks price or says \"I mean KommuAssist\".
- **Partner installers (FAQ-only):** JB partner — Mr Tey Hyper Auto, Skudai (Lot CP2 Best Mart, +60 12-787 5885); Penang — SAFCA Penang (Facebook contact; no public street address found).
- **Context architecture:** removed regex topic stickiness (`infer_session_topic`, `update_session_topics`, `get_session_topics`), per-turn FAQ retrieval hints, and FAQ-first-on-message-1 shortcut; model uses full FAQ + full session history instead.
- **Agent loop:** removed server grounding gate (`ungrounded_answer_blocked`, `vehicle_nudge`, `pick_clarify_for_intent`); the model’s `direct_answer` is sent as-is even without `source_ids` or tool calls. Path A clarify validation (`finalize_clarifying_answer`) unchanged.
- **FAQ (`master_faq.md`):** added `regional_installer` and `regional_installer_followup` intents (Penang/outstation partner installers, aliases for "one in penang"); narrowed `install_booking` to HQ appointments; clarified `self_install` vs partner vs HQ.

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
- **Language:** message routes auto-adapt to the user.
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
