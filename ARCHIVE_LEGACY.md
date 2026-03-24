# Legacy Archive Guide

This repository was reorganized to keep the current architecture easy to navigate.

## What this folder means

`archive_legacy/` contains historical components that were moved out of the active runtime path.

These files are retained for:

- historical reference
- rollback safety
- migration context

They are **not** part of the current production flow.

## Current architecture entrypoints

Use these first:

- `app.py`
- `api/v2/agent_message.py`
- `api/v2/agent_query.py`
- `support_runtime/`
- `services/kai_service.py` (Chatwoot parity logic)

## Archived content map

- `archive_legacy/docs/` — prior architecture notes
- `archive_legacy/core_router/` — deprecated router engine
- `archive_legacy/skills_runtime/` — deprecated skill-loader runtime and legacy skill handlers

## If you need to restore legacy behavior

Do not copy files ad hoc. Restore intentionally and re-run:

- parity tests
- runtime tests
- endpoint compatibility checks

