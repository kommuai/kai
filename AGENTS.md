# AGENTS Guide

## Operator surface (edit content here)

See [`docs/OPERATOR.md`](docs/OPERATOR.md).

| Change | Path |
|--------|------|
| Agent instructions | `agent_workspace/01_core/system_prompt.md` |
| FAQ / policy | `agent_workspace/02_knowledge/faq/master_faq.md` |
| Chat copy (LA, resume, footers) | `agent_workspace/05_copy/chat_copy.yaml` |
| Defaults | `agent_workspace/settings.yaml` + `.env` |
| Enabled tools | `agent_workspace/03_tools/tools.yaml` (`active_profile` + `profile_overrides`) |
| Channels | `agent_workspace/04_channels/handover.yaml` |
| Manifest | `agent_workspace/00_manifest.yaml` |
| Plugins | `agent_workspace/03_tools/plugins/<id>/main.py` |

Engine builtins are generic (`kai/support_runtime/tools/catalog.py`). Legacy tool ids (e.g. `search_kommu_support`) map via aliases.

Then `POST /admin/refresh-sop` or restart after workspace edits.

```bash
python3 tools/kai doctor
python3 -m kai.cli port-check   # deps + startup hints for this workspace
```

New tenant checklist: [`docs/PORTING.md`](docs/PORTING.md). Core vs optional deps: `requirements.txt` + `requirements-optional.txt`.

## Architecture boundaries

- `kai/api/v2/`: HTTP chat and admin routes (`POST /agent/message`, `/admin/*`, `/v2/agent/query`).
- `kai/content/`: loads workspace prompts, FAQ, copy.
- `kai/settings/`: centralized configuration (`config.py` re-exports for compat).
- `kai/services/kai_service.py`: `pre_router`, outbound footers; `turn_ingest.py` for session writes.
- `kai/app_factory.py` + `kai/engine/`: lifespan startup, schedulers, `get_workspace_features()`.
- `kai/support_runtime/`: FAQ compiler, ReAct agent loop, tools package (`tools/catalog|handlers|registry`).
- `kai/core/outbound_delivery.py`: WhatsApp 4096-char cap via `KaiService.finalize_reply`.

## Restricted edits

- Do not break `POST /agent/message` payload/response envelope (n8n/WhatsApp).
- Keep `pre_router` before `support_runtime_service.execute`.
- Do not reintroduce removed legacy paths (`main_conversation`, `archive_legacy`, `IntentRouter`).

## Verification

```bash
pytest tests/test_architecture_import_boundaries.py tests/test_chat_copy_parity.py \
  tests/test_prompt_assembly_snapshot.py tests/test_agent_loop.py tests/test_api_contracts.py -q
```
