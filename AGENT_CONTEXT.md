# Kai — Agent context

Session log for this repo. Global handoff: `/home/ting/system-notes/AGENT_CONTEXT.md`.

## 2026-03-27 — Integrate SMARTSERVA visitor-pass automation into Kai tools

- Intent: when users ask for building-entry QR/pass links, let Kai call the SMARTSERVA automation and return the generated link directly.
- Files changed:
  - `support_runtime/agent_tools.py`
    - Added tool registration: `create_visitor_pass` with schema (`visit_date`, `visit_time`, optional `unit_id`).
    - Added handler `create_visitor_pass(...)` that runs `/home/ting/workspace/smartserva/create_visitor_pass.py` via subprocess and returns normalized output (`visitor_pass_link`, visitor metadata).
    - Added tool-timeout/file-missing/failure handling.
  - `support_runtime/agent_prompts.py`
    - Added explicit tool strategy section for building-entry QR/link intents: ask date/time if missing, call `create_visitor_pass`, return link.
  - `tests/test_agent_tools.py`
    - Added assertions that registry includes `create_visitor_pass`.
    - Added success/failure handler tests with mocked subprocess execution.
- Validation:
  - `python3 -m pytest -q tests/test_agent_tools.py tests/test_agent_loop.py` → `8 passed`.
  - Live tool smoke via registry call with SMARTSERVA creds env set returned `ok: True` and a real `visitor_pass_link`.
  - Prompt/tool wiring check confirms both `create_visitor_pass` and strategy text are present in built system prompt.
- Next:
  - Ensure runtime environment where Kai runs has `SMARTSERVA_USERNAME` and `SMARTSERVA_PASSWORD` set.
  - Optional override vars: `KAI_SMARTSERVA_TOOL_PATH`, `KAI_SMARTSERVA_TOOL_TIMEOUT_SECONDS`.

## 2026-03-27 — Default current date/time when missing for visitor-pass requests

- Intent: if user asks for building-entry QR/pass link without date/time, proceed using current time instead of asking follow-up.
- Files changed:
  - `support_runtime/agent_tools.py`
    - `create_visitor_pass` schema no longer requires `visit_date`/`visit_time`.
    - Handler now accepts optional `visit_date`/`visit_time` and only passes CLI flags when provided (empty => script defaults).
  - `support_runtime/agent_prompts.py`
    - Updated guidance: missing visit date/time should default to current local date/time and proceed.
  - `tests/test_agent_tools.py`
    - Added test ensuring empty args call omits `--date`/`--time` and still succeeds.
  - `../smartserva/create_visitor_pass.py`
    - `--date` and `--time` made optional.
    - Missing values now default to current local date/time in schedule parsing.
- Validation:
  - `python3 -m py_compile /home/ting/workspace/smartserva/create_visitor_pass.py`
  - `python3 -m pytest -q tests/test_agent_tools.py tests/test_agent_loop.py` → `9 passed`
  - Live runtime call `reg.call("create_visitor_pass", {})` returned `ok: True` with generated link and current timestamped schedule.

## 2026-03-26 — SOP resync command lookup

- Intent: User asked for the executable command to resync SOP with `master_faq`.
- Verified script: `tools/force_sop_sync.py` exists and is executable.
- Confirmed usage in `README.md` section "Force SOP merge-sync now (local executable)".
- Recommended command from repo root: `./tools/force_sop_sync.py` (or `python3 tools/force_sop_sync.py`).

## 2026-03-26 — SOP merge sync (8am)

- Added `core/sop_sync_merge.py` to pull local+Google SOP regions, parse/merge with field-level Google precedence, re-render schema, write local, write back to Google, and track hashes/date in `rag/sop_sync_state.json`.
- Added `app.py` scheduled task (`@repeat_every(seconds=600)`) gated by `KAI_SOP_MERGE_SYNC_ENABLED`; runs once per day at configured time (`KAI_SOP_MERGE_SYNC_HOUR`/`KAI_SOP_MERGE_SYNC_MINUTE`) using `TZ_REGION`.
- Added `core.faq_markdown.render_master_faq_schema()` to render canonical schema blocks.
- Added tests in `tests/test_sop_sync_merge.py`.
- Validation: `python3 -m pytest -q tests/test_sop_sync_merge.py tests/test_faq_markdown.py tests/test_api_contracts.py` -> 14 passed.

## 2026-03-26 — Backlog logging even when user resolves

- Updated diagnostic instructions in `support_runtime/agent_prompts.py` so `log_backlog` can be called once `device` and `car` are known even if the user claims it’s resolved, and to confirm to the user after logging.
- Added tool-side readiness gating in `support_runtime/agent_tools.py` for `log_backlog`: returns `ok:false` with `log_backlog_not_ready_missing_device_car` unless `device` and `car` are known (not `Unknown`).
- Added unit tests in `tests/test_log_backlog_readiness.py`.
- Validation: `python3 -m pytest -q tests/test_log_backlog_readiness.py` -> 3 passed.

## 2026-03-26 — Test drive Calendly

- `master_faq.md` `test_drive` intent: answer includes https://calendly.com/kommuassist/test-drive; extra aliases for booking wording.

## 2026-03-26 — log_backlog 4-column revamp

- Updated `log_backlog` tool and handler to write only 4 columns to `Chatbot Backlog`: timestamp, device, car, issue summary.
- Updated backlog similarity lookup to match column D.
- Added/updated unit tests in `tests/test_log_backlog_readiness.py`.
- Validation: `python3 -m pytest -q tests/test_log_backlog_readiness.py tests/test_agent_tools.py tests/test_tech_backlog_enrichment.py`.

## 2026-03-26 — log_backlog DeepSeek D/E 5-column revamp

- Intent: Call DeepSeek to generate `D` (technical descriptive problem) and `E` (reproduction steps paragraph), then write exactly 5 columns to the backlog sheet (`A:E`) with readiness gating preserved.
- Files changed: `support_runtime/agent_tools.py` (DeepSeek call + JSON parsing fallback + tool-side argument mapping), `support_runtime/tech_backlog.py` (`append_backlog_issue` now writes `A:E`; similarity lookup reads `A:E` and matches on column `D`), `tests/test_log_backlog_readiness.py` (mock DeepSeek and assert `issue_description` + `reproduction_steps` args).
- Validation: `python3 -m pytest -q tests/test_log_backlog_readiness.py` → `3 passed`; `python3 -m pytest -q tests/test_tech_backlog_tabs.py tests/test_tech_backlog_enrichment.py` → `4 passed`.

## 2026-03-26 — live backlog 8-case simulation

- Ran 8 `log_backlog` calls: 5 successful writes and 3 readiness blocks.
- Successes: `ready_1` → `A1:E1`, `ready_2` → `A2:E2`, `ready_3` → `A3:E3`, `ready_4` → `A4:E4`, `ready_5` → `A5:E5`.
- Blocked: `not_ready_1_device_unknown`, `not_ready_2_car_unknown`, `not_ready_3_both_unknown` → `log_backlog_not_ready_missing_device_car`.

## 2026-03-26 — executable helper for forced SOP sync

- Added `tools/force_sop_sync.py` as a runnable executable wrapper for `sync_sop_regions()`.
- Usage: `./tools/force_sop_sync.py` from repo root.
- Validation: command runs successfully and returns structured JSON sync result with `ok: true`.

## 2026-03-26 — factual-answer guardrails

- Updated `support_runtime/agent_prompts.py` to resolve conflicting instructions and prefer grounded factual claims with concise uncertainty when unsupported.
- Updated `support_runtime/agent_loop.py` to remove plain-text direct-answer fallback and add a lightweight grounding gate: non-chitchat `direct_answer` needs evidence (`source_ids` or successful tool observation), otherwise downgraded to clarifying question / lower confidence.
- Added tests in `tests/test_agent_loop.py` for plain-text fallback behavior and source-backed direct answers.
- Validation: `python3 -m pytest -q tests/test_agent_loop.py` -> 4 passed; manual smoke script verified behavior on fabricated contact example.

## 2026-03-26 — sales psychology + LA-only live-agent footer

- Updated `support_runtime/agent_prompts.py` with a lightweight pricing strategy: for RTO, lead with RM175/month + RM1,999 deposit; mention RM4,999 cash when explicitly asked.
- Updated `agent_workspace/02_knowledge/faq/master_faq.md`: revised `pricing` and `rto_details`, and added new `full_cash_price` intent for explicit cash-price asks.
- Recompiled canonical artifacts (`agent_workspace/compiled/intents.json`, `agent_workspace/compiled/kb_chunks.jsonl`, related compiled outputs) via `compile_canonical_knowledge()`.
- Updated `services/kai_service.py` to show `For Live Agent, type LA` (BM equivalent taip LA) and make the live-agent trigger LA-only (typing `KA1`/`KA2` will no longer hand over).
- Validation: `python3 -m pytest -q tests/test_agent_loop.py tests/test_intent_accuracy.py` -> 5 passed; manual simulation confirms LA-only footer string.

## 2026-03-26 — vehicle support false-negative fix (official list first)

- Updated `services/kai_service.py` to check official support evidence (`kommu.ai/support` text match by model/year) before generic RAG fallback in car-support flow.
- Added tests in `tests/test_vehicle_support_matching.py` for positive model/year match and year mismatch guard.
- Validation: `python3 -m pytest -q tests/test_vehicle_support_matching.py tests/test_vehicle_support_evidence.py tests/test_agent_loop.py` -> 8 passed.

## 2026-03-26 — active support_runtime path fix for Alphard 2020

- Updated `support_runtime/agent_tools.py` `search_kommu_support` with explicit official vehicle matching + year-range logic so active `/agent/message` route can recognize listed models/years reliably.
- Added test `tests/test_vehicle_support_official_match.py` (Toyota Alphard 2020 match).
- Validation: `python3 -m pytest -q tests/test_vehicle_support_official_match.py tests/test_vehicle_support_evidence.py tests/test_agent_loop.py` -> 7 passed.
- Note: server restart required; without restart live requests still use old code.

## 2026-03-25 (follow-up) — Google Docs writeback

- Ran `push_master_faq_to_google_doc()` again; result `ok: true`, `mode: sync_region_only`.

## 2026-03-25 — Knowledge, backlog, tools overhaul

- **Summary:** Master FAQ expanded; dynamic FAQ blocks now support `valid_from` / `valid_until` / `priority`, compiled into searchable chunks; backlog append uses columns A–H; new `read_bukapilot_file` tool; agent loop allows 80k-char tool results for that tool; system prompt updated.
- **Validation:** `timeout 900 python3 -m pytest -q` → 55 passed. Google Docs FAQ writeback succeeded when enabled.
- **Next:** Ensure spreadsheet headers match A–H if operators rely on row 1 labels.

## 2026-03-27 — QR link runtime fix verified

- Root cause found for QR generation failure in runtime path: SmartServa env keys in `.env` had invalid spacing (`KEY = value`) so runtime did not load them correctly.
- Updated `.env` formatting for SmartServa keys to strict `KEY=value`.
- Validation (runtime repro): `support_runtime_service.execute("can i have the access qr now", ...)` now reaches `create_visitor_pass`; subsequent failure shifted to SmartServa booking-window rule, confirming credentials are now loaded.

## 2026-03-27 — Docker readiness for visitor-pass tool

- Intent: ensure containerized Kai can run `create_visitor_pass` with required dependencies and script path.
- Files changed:
  - `requirements.txt`: added `ddddocr` dependency.
  - `support_runtime/agent_tools.py`: updated `create_visitor_pass` script path resolution to prefer `/app/smartserva/create_visitor_pass.py` in containers, with local fallback.
  - `docker-compose.yml`: mounted `../smartserva` into container as read-only `/app/smartserva`.
  - `.dockerignore`: added to reduce build context size and avoid shipping local artifacts/secrets.
- Validation:
  - `python3 -m py_compile support_runtime/agent_tools.py` -> OK.
  - Runtime smoke call `reg.call("create_visitor_pass", {})` -> `ok=True` (with local env available).
  - `docker compose build kai` started successfully and reached dependency installation stage with `ddddocr` included.

## 2026-03-27 — Removed hardcoded SmartServa path defaults

- Intent: make `create_visitor_pass` path resolution production-portable across different host layouts.
- File changed:
  - `support_runtime/agent_tools.py`
    - Removed machine-specific absolute fallback paths.
    - Resolution order is now:
      1) `KAI_SMARTSERVA_TOOL_PATH` env var
      2) repo-relative discovery (`<kai_repo>/smartserva/create_visitor_pass.py`, sibling `../smartserva/create_visitor_pass.py`, and `cwd/smartserva/create_visitor_pass.py`)
    - If unresolved, returns explicit config error: `missing_smartserva_tool:set_KAI_SMARTSERVA_TOOL_PATH_or_mount_smartserva`.
- Validation:
  - `python3 -m py_compile support_runtime/agent_tools.py` -> OK.
