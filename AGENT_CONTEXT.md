# Kai — Agent context

## 2026-05-22 — ReAct access to canonical FAQ answers

- **Intent:** ReAct loop can use the same compiled FAQ canonical answers as the FAQ-first shelf (not only via blind LLM paraphrase).
- **Files:** `support_runtime/canonical_faq.py` (shared pick/extract/hint); `agent_tools.search_faq` adds `canonical_answer` per row + `best_canonical`; `service.execute` injects **Authoritative FAQ match** into `session_context` before every `graph.run`; `agent_prompts.py` documents `best_canonical` + injected block.
- **Paths:** FAQ-first (first message, link/video) unchanged; ReAct gets preloaded canonical hint + richer `search_faq` tool output.
- **Validation:** `pytest tests/test_canonical_faq.py tests/test_session_react_context.py -q` (unit parts) pass.

## 2026-05-22 — Follow-up turns: always ReAct + short-term memory in LLM context

- **Intent:** From the **second message** in a session onward, always route through `ReActAgentLoop` (skip FAQ-first shortcut) so multi-turn threads keep tool use + prior context. Inject **session summary** and **memory_facts** into the agent (same data `run_rag_dual` used in legacy path but was missing from support runtime).
- **Files:** `session_state.py` (`build_short_term_context`); `support_runtime/service.py` (`is_follow_up = bool(history)`, FAQ-first only when history empty, record user turn before `graph.run`, pass `session_context`); `support_runtime/agent_loop.py` (`session_context` system message, `MEMORY_DEPTH` history window, map `bot`→`assistant`, avoid duplicate current user line); `support_runtime/agent_prompts.py` (session memory rules); `tests/test_session_react_context.py`; `tests/test_support_runtime.py` (FAQ-first first message only).
- **Validation:** `pytest tests/test_session_react_context.py tests/test_memory_extension.py -q` → 8 passed; `pytest tests/test_support_runtime.py::SupportRuntimeTests::test_faq_first_returns_video_link_on_first_message_only -q` → 1 passed; fast suite `pytest tests/ --ignore=tests/test_support_runtime.py -q` → 99 passed.

## 2026-05-21 — Anti-annoyance pass: intent-aware clarify + footer discipline + chitchat expansion

- **Intent (P0 from chat-history analysis):** Stop the "Reply with your car brand, model, and year — or your dongle ID..." line from leaking into office/pricing/warranty/QR/greeting turns; stop the `For Live Agent, type LA` footer from nagging every reply after turn 7 (incl. on grounded canonical answers and visitor-pass links); make chitchat detection catch `test`, `howdy`, `hai`, emoji, Malay greetings.
- **New module:** `support_runtime/clarify_intent.py` — pure-function `pick_clarify_for_intent(text, lang)` routes ungrounded clarify by keyword family: office/hours, pricing/RTO, supported list (→ kommu.ai/support), warranty/dongle, install/video, QR/visitor pass, order/payment, diagnostic, vehicle (only when query is actually vehicle-y), else a friendly multi-option menu. BM phrasing for each branch.
- **agent_loop.py:** wires `pick_clarify_for_intent` into the `ungrounded_answer_blocked` path so the substitute clarify matches the *user's* topic; `_looks_like_chitchat` markers expanded (`test`, `testing`, `howdy`, `hai`, `helo`, `okie`, `noted`, `terima kasih`, `selamat pagi/petang/malam`, single-emoji ≤3 chars).
- **services/kai_service.py:** `add_footer(..., *, suppress: bool = False)`; turn threshold raised `7 → 10`. Default behavior unchanged for `pre_router` callers.
- **api/v2/agent_message.py:** sets `suppress_footer = (capability_used == "canonical_answer") or (decision == "direct_answer" and source_ids)` and passes it through. This kills LA-footer spam on FAQ-first answers and grounded tool replies without touching the unhappy paths.
- **Tests:** `tests/test_clarify_intent.py` (13 cases: every branch + chitchat expansion).
- **Validation:** `pytest tests/test_clarify_intent.py -q` → 13 passed; fast suite `pytest tests/ --ignore=tests/test_support_runtime.py -q` → 96 passed (98 subtests); slow live-LLM `pytest tests/test_support_runtime.py -q` → 12 passed in 88 s. Total 121/121 with no regressions.
- **Architectural note:** Two responsibilities stay separate — `clarify_validation.py` validates/repairs LLM-emitted clarify text; `clarify_intent.py` chooses which clarify to ask when grounding is missing. The footer suppression signal is computed at the API boundary (the only place that has `RuntimeResult`), so service-layer callers (`pre_router`) keep their current footer behavior.
- **Deferred (P1+ from analysis):** broaden FAQ-first beyond video/link; WhatsApp message debouncing; honest-escalation prompt; regression eval set.

## 2026-05-13 — SmartServa QR: always use newest visitor row (fix stale/expired links)

- **Intent:** Visitor passes use fixed display name `Kommu`; listing lookup returned the **first** HTML match, so Kai could surface an **old/expired** `visitor_pass.php` link after a new `add_vi`.
- **Change:** `integrations/smartserva/create_visitor_pass.py` — prefer visitor id from `add_vi` JSON when present; else pick **highest numeric** `v="..."` row among name matches. `tests/test_smartserva_visitor_pick.py` covers selection.
- **Validation:** `pytest tests/test_smartserva_visitor_pick.py tests/test_agent_tools.py -q` → pass.

## 2026-04-11 — Google Drive SOP sync (re-run)

- Intent: Merge remote `sop-sync` region into `master_faq.md`, write back to Google Doc.
- Actions: `cd /home/ting/workspace/kai && ./tools/force_sop_sync.py` → `ok: true`, writeback `ok: true` (doc `1Y80JRyFIQrb99XNgPIUA3p0cGy4KUyoAhG1vdJMO0fs`).
- Diff vs previous commit (FAQ): same single-line wording as prior micro-sync — intent `kommuassist_installation_guide` answer **15 min briefing** → **15 min tutorial/briefing**.
- Next: `compile_canonical_knowledge()` if runtime KB should match disk.

## 2026-03-29 — Clarifying: schema `question`, validate → repair → compress → span → fallback

- **Intent:** Stop soft preambles on `clarifying_question` (hedge phrases, “accurate info”, “one more detail”); user-visible ask must be a single concrete question ending in `?`.
- **Files:** `support_runtime/clarify_validation.py` (hedge list, `is_valid_clarifying_text`, `last_question_span`, `compress_to_one_question`); `support_runtime/agent_loop.py` (`finalize_clarifying_answer`, `metadata["clarify_sanitize"]` tags: `clarify_repair`, `clarify_compress`, `clarify_last_question_span`, `clarify_fallback_generic`); `support_runtime/agent_prompts.py` (response format: prefer `question` for clarify); tests `tests/test_clarify_validation.py`, `tests/test_agent_loop.py` (incl. hedge repair), `tests/test_agentic_understanding.py` (mock includes `source_ids` so ungrounded clarify does not override `direct_answer`).
- **Validation:** `pytest tests/test_clarify_validation.py tests/test_agent_loop.py -q` → pass; full `pytest tests/` → 92 passed (~3.5 min, includes `test_support_runtime.py`).

## 2026-04-04 — Google Drive SOP sync (micro-diff)

- Intent: Merge Google Doc `sop-sync` region into `master_faq.md` and write back; report diff vs local.
- Actions: `./tools/force_sop_sync.py` → `ok: true`, Google writeback `ok: true` (doc `1Y80JRyFIQrb99XNgPIUA3p0cGy4KUyoAhG1vdJMO0fs`, `sync_region_only`).
- Diff: single line in intent `kommuassist_installation_guide` — answer text **15 min briefing** → **15 min tutorial/briefing** (Google wins per merge rules).
- Next: Run `compile_canonical_knowledge()` if runtime KB should match disk.

## 2026-04-03 — Kai tone: direct clarifying questions (no “more info” hedging)

- Intent: Stop vague openers (“can I get more info”, “could you share more detail”); ask one concrete question; align loop fallbacks.
- Files changed: `support_runtime/agent_prompts.py` (personality + rules); `support_runtime/agent_loop.py` (no_signal / post-tool-parse / ungrounded fallback strings).
- Validation: `pytest tests/test_agent_loop.py -q` → 4 passed.

## 2026-03-29 — Visitor pass: plain URL + fixed SmartServa name/phone

- Intent: QR/visitor links stay tappable (strip markdown bold around https URLs in outbound replies); SmartServa visitor row uses fixed name `Kommu` and phone `1`.
- Files changed: `services/kai_service.py` (`strip_bold_markdown_wrapping_around_urls`, `add_footer`); `support_runtime/agent_prompts.py`; `support_runtime/agent_tools.py` (`create_visitor_pass` tool description); `integrations/smartserva/create_visitor_pass.py`; `tests/test_support_runtime.py`.
- Validation: `pytest tests/test_support_runtime.py::SupportRuntimeTests::test_strip_bold_markdown_wrapping_around_urls tests/test_agent_tools.py -q` → 6 passed.

## 2026-03-31 — SOP-side fix then force resync

- Intent: `./tools/force_sop_sync.py` was failing because Google SOP had `## intent: collaboration` in legacy format (plain body line, no `answer:` key). User requested fixing SOP side then resync.
- Files changed:
  - `core/faq_markdown.py` — parser now accepts legacy intent body as answer when `aliases:`/`answer:` headers are absent.
  - `agent_workspace/02_knowledge/faq/master_faq.md` — updated by successful force sync (Google merge/writeback).
- Validation:
  - `./tools/force_sop_sync.py` → `ok: true`, Google writeback `ok: true`, counts now include 40 intents.
  - `pytest tests/test_faq_markdown.py -q` → 4 passed.
- Note: resync introduced a large content diff in `master_faq.md` (Google-side content took precedence in merged region).

## 2026-03-29 — Live-agent handback FAQ learning + remove legacy Chatwoot FAQ candidates

- Intent: Replace tag-poll `faq_candidates` / admin publish-to-`master_faq` with a **session-backed** flow: on `resume` after live handoff (or after AI escalation handover), pop the human-window transcript and append a **unified diff** suggestion to `agent_learnt_faq.md` (not compiled into KB). Align **AI escalation** with **frozen** + same segment capture.
- Files changed: removed `support_runtime/faq_feedback.py`, `tools/faq_approval_cli.py`; `session_state.py` (DROP `faq_candidates`, human segment helpers); `config.py` (`AGENT_LEARNT_FAQ_PATH`, `KAI_FAQ_LEARN_*`); `support_runtime/faq_learn.py` (new); `services/kai_service.py` (pre_router segment + deduped user history vs `execute`); `services/chatwoot_handover.py` (`extract_chatwoot_conversation_id`); `api/v2/agent_message.py` (removed admin FAQ routes; escalate → segment + freeze); `app.py` (removed FAQ poll task); `agent_workspace/02_knowledge/faq/agent_learnt_faq.md`; `README.md`; tests `test_faq_learn.py`, `test_pre_router.py`, `test_chatwoot_parity_contract.py`, `test_diagnostic_and_faq_loop.py`.
- Validation: `pytest tests/test_faq_learn.py tests/test_diagnostic_and_faq_loop.py tests/test_pre_router.py tests/test_chatwoot_live_handover.py tests/test_chatwoot_parity_contract.py -q` → pass.
- Breaking: `/admin/faq-feedback/*` and `/admin/faq-candidates/*` removed; `faq_candidates` table dropped on `init_db`.
- Next: Optional n8n hook to POST **human_agent** lines into `append_human_segment_turn`; merge job from `agent_learnt_faq.md` → `master_faq.md`.


Session log for this repo. Global handoff: `/home/ting/system-notes/AGENT_CONTEXT.md`.

## 2026-03-29 — Install positioning: self-install encouraged (not HQ-default)

- Intent: Stop implying Kommu always installs the device or pushing appointment booking; Kommu encourages **self-install** with HQ as **optional** help.
- Files changed: `agent_workspace/02_knowledge/faq/master_faq.md` (`install_booking`, `installation_time`, `kommuassist_installation_guide` intro + warranty bullet; aliases `install myself`, `self install`, `diy install kommuassist`); `support_runtime/agent_prompts.py` (Products install line + Rules **Installation tone**); `templates.py` `reply_buy` EN/BM; `services/kai_service.py` supported-car follow-up copy.
- Validation: `compile_canonical_knowledge()` OK; `pytest tests/test_faq_markdown.py` → 4 passed.

## 2026-03-29 — Installation chatbot live validation (20 Q) + email

- Intent: Build **20** diverse user questions tied to the Installation & Briefing SOP (standard steps, USB swap, cluster errors, fingerprints, Malay phrasing, briefing topics), run **live** `SupportRuntimeService.execute` (same stack as `/v2/agent/message`), email full Q+A to **support@kommu.ai** with subject **chatbot installation validation test**.
- Files changed:
  - `tools/run_install_validation_batch.py` — batch runner writing JSON path (default `/tmp/...` or argv).
- Artifacts (not committed): `/tmp/kai_install_validation_report.json`, `/tmp/chatbot_installation_validation_body.txt`.
- Validation: batch finished successfully; `email_ops` IMAP send reported `status: sent` to `support@kommu.ai`.
- Security note: email skill `config.runtime.json` had plaintext credentials in repo; recommend rotation and `chmod 600` + gitignore pattern for local secrets copy.
- Next: Optional — gzip long reports or attach JSON; tune questions from support feedback.

## 2026-03-29 — Installation SOP → master_faq + compile

- Intent: Pull Kommu **Installation & Briefing SOP** from `support@kommu.ai` Google Drive (rclone remote), condense into Kai knowledge, update `master_faq.md`.
- Source file: `AI-Agent Public Knowledge/Standard Operating Procedures/Installation & Briefing SOP.docx` (Relay + Vision + Kommu Power workflow; fingerprint table as in doc).
- Files changed:
  - `agent_workspace/02_knowledge/faq/master_faq.md` — new intent `kommuassist_installation_guide` (inside `sop-sync` region); `Last updated` date; provenance HTML comment after sync region.
  - `agent_workspace/compiled/intents.json`, `kb_chunks.jsonl`, `workflows.json`, `tool_policies.json` — regenerated via `compile_canonical_knowledge()`.
- Validation:
  - `parse_master_faq_schema` on full `master_faq.md` OK; `kommuassist_installation_guide` present.
  - `python3 -c "from support_runtime.compiler import compile_canonical_knowledge; ..."` → 38 intents, 39 chunks.
  - `python3 -m pytest tests/test_faq_markdown.py -q` → 4 passed.
- Note: `./tools/force_sop_sync.py` **failed** here because Google SOP region parse hits invalid `collaboration` intent (missing answer) in the remote doc — unrelated to this FAQ edit. Use local compiler for KB rebuild until Google doc is fixed.
- Next: Repair Google Doc SOP region or skip merge; optionally add official video URL if marketing provides one.

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

- Updated `support_runtime/agent_prompts.py` with a lightweight pricing strategy: for RTO, lead with RM175/month + RM1,999 deposit; mention RM4,999 **one-off** when explicitly asked.
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

## 2026-03-27 — SmartServa moved inside Kai repo

- Intent: reorganize project by moving SmartServa assets into Kai so production deploy does not depend on sibling directories.
- New location:
  - `integrations/smartserva/create_visitor_pass.py`
  - `integrations/smartserva/README.md`
  - `integrations/smartserva/LOGIN_PLAN.md`
  - `integrations/smartserva/AGENT_CONTEXT.md`
- Runtime wiring updates:
  - `support_runtime/agent_tools.py` discovery now prioritizes `integrations/smartserva/create_visitor_pass.py`.
  - `docker-compose.yml` removed external mount `../smartserva:/app/smartserva:ro`.
  - `README.md` updated with integration location + optional `KAI_SMARTSERVA_TOOL_PATH`.
- Security cleanup:
  - Removed old external runtime artifact containing session cookies (`workspace/smartserva/runtime/login_success_latest.json`) instead of migrating it.
- Validation:
  - `python3 -m py_compile support_runtime/agent_tools.py integrations/smartserva/create_visitor_pass.py` -> OK.
  - `AgentToolRegistry.call("create_visitor_pass", {})` -> `ok=True`, `visitor_pass_link` present.

## 2026-03-28 — Per-turn wall clock in system prompt

- `support_runtime/agent_prompts.py`: `local_clock_block()` injects current Malaysia-local date/time (`TZ_REGION` / `TZ`) before tool list.
- `support_runtime/service.py`: rebuilds `system_prompt` on each `execute()` so “today/tomorrow” stays current.
- Tests: `pytest tests/test_agent_loop.py` → 4 passed.
