# Kai — Agent context

Session log for this repo. Global handoff: `/home/ting/system-notes/AGENT_CONTEXT.md`.

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

## 2026-03-25 (follow-up) — Google Docs writeback

- Ran `push_master_faq_to_google_doc()` again; result `ok: true`, `mode: sync_region_only`.

## 2026-03-25 — Knowledge, backlog, tools overhaul

- **Summary:** Master FAQ expanded; dynamic FAQ blocks now support `valid_from` / `valid_until` / `priority`, compiled into searchable chunks; backlog append uses columns A–H; new `read_bukapilot_file` tool; agent loop allows 80k-char tool results for that tool; system prompt updated.
- **Validation:** `timeout 900 python3 -m pytest -q` → 55 passed. Google Docs FAQ writeback succeeded when enabled.
- **Next:** Ensure spreadsheet headers match A–H if operators rely on row 1 labels.
