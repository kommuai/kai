# Agent workspace manifest (pointer)

**Primary config:** [`00_manifest.yaml`](00_manifest.yaml) — tenant id, paths, knowledge mode, `sop_sync`, `session_store`.

This Markdown file is kept for operator notes only. Runtime loads YAML first.

## Session storage

Configured in `00_manifest.yaml` under `session_store` (default SQLite at `data/sessions.db`). Override with `SESSION_DB_PATH` in `.env`.

## SOP region sync

Markers in `02_knowledge/faq/master_faq.md` between `<!-- sop-sync:start -->` and `<!-- sop-sync:end -->`. Enable scheduled merge via `KAI_SOP_MERGE_SYNC_ENABLED` and `sop_sync.enabled` in YAML.
