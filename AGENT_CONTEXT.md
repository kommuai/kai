# Kai — Agent context

Session log for this repo. Global handoff: `/home/ting/system-notes/AGENT_CONTEXT.md`.

## 2026-03-26 — Test drive Calendly

- `master_faq.md` `test_drive` intent: answer includes https://calendly.com/kommuassist/test-drive; extra aliases for booking wording.

## 2026-03-25 (follow-up) — Google Docs writeback

- Ran `push_master_faq_to_google_doc()` again; result `ok: true`, `mode: sync_region_only`.

## 2026-03-25 — Knowledge, backlog, tools overhaul

- **Summary:** Master FAQ expanded; dynamic FAQ blocks now support `valid_from` / `valid_until` / `priority`, compiled into searchable chunks; backlog append uses columns A–H; new `read_bukapilot_file` tool; agent loop allows 80k-char tool results for that tool; system prompt updated.
- **Validation:** `timeout 900 python3 -m pytest -q` → 55 passed. Google Docs FAQ writeback succeeded when enabled.
- **Next:** Ensure spreadsheet headers match A–H if operators rely on row 1 labels.
