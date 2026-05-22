# Porting Kai to another business

Kai is **tenant-agnostic at runtime**: behavior comes from `agent_workspace/`, not from hard-coded brand strings in the engine.

## Quick checklist

1. **Scaffold workspace**
   ```bash
   python3 tools/kai init --workspace ./agent_workspace
   ```
2. **Edit manifest** — `00_manifest.yaml`: `tenant_id`, `display_name`, paths, `tools_enabled` fallback.
3. **Tools** — `03_tools/tools.yaml`: pick `active_profile` or list tools; set `profile_overrides` URLs/repos (no engine code changes).
4. **Knowledge** — `02_knowledge/faq/master_faq.md`, then `python3 tools/kai compile`.
5. **Channels** — `04_channels/handover.yaml` (office hours, handover keywords, media rules).
6. **Copy** — `05_copy/chat_copy.yaml` and `01_core/system_prompt.md`.
7. **Env** — copy `.env.example` → `.env`; set `AGENT_WORKSPACE`, LLM keys, integration vars only for enabled tools.
8. **Validate**
   ```bash
   python3 tools/kai doctor
   python3 -m kai.cli port-check
   ```

## Dependencies by feature

| Feature | Install | Env / workspace |
|--------|---------|-----------------|
| Core chat | `requirements.txt` | `OPENAI_API_KEY` or provider in settings |
| Warranty / Sheets | `requirements-optional.txt` | Google service account + sheet IDs |
| Qdrant RAG (if used) | optional | `QDRANT_*` |
| Visitor pass plugin | optional + `ddddocr` | Plugin under `03_tools/plugins/<id>/` |
| GitHub backlog tools | core `requests` | `KAI_GITHUB_REPO` / `KAI_GITHUB_BRANCH` (legacy `BUKAPILOT_*` still works) |

Docker (full Kommu-style stack):

```bash
pip install -r requirements.txt -r requirements-optional.txt
```

## Startup tuning

| Variable | Effect |
|----------|--------|
| `KAI_STARTUP_COMPILE=0` | Skip FAQ compile on boot (use when image build already ran `kai compile`) |
| `KAI_STARTUP_COMPILE=auto` | Compile only if compiled KB artifact is missing |
| `KAI_STRICT_STARTUP=1` | Fail process if workspace validation has errors |
| `KAI_SOP_MERGE_SYNC_ENABLED=1` | Daily SOP region merge (Kommu-specific; off for new tenants) |
| `KAI_SCHEDULER_ENABLED=0` | Disable daily KB refresh asyncio task (dev / single-shot containers) |

Warranty sheet cache is warmed **only** when `lookup_sheet_record` (or legacy `lookup_warranty`) is enabled in `tools.yaml`.

Docker images should run `kai compile` at build time and set `KAI_STARTUP_COMPILE=auto` (see repo `Dockerfile`).

## What stays in the repo vs workspace

| Repo (engine) | Workspace (tenant) |
|---------------|-------------------|
| ReAct loop, HTTP routes | FAQ, system prompt, copy |
| Builtin tool handlers | Tool list, params, plugins |
| Compiler, retrieval | Manifest paths, settings merge |
| CLI `doctor` / `init` | Handover rules, branding |

## Packs (optional)

See `packs/README.md` for bundling a pre-filled workspace (e.g. Kommu) without forking the engine.

## Support API surface

Unchanged for integrators:

- `POST /v2/agent/message` — primary chat path
- `GET /health`, `GET /ready` — probes

Point `AGENT_WORKSPACE` at a different directory per deployment; one process = one tenant.
