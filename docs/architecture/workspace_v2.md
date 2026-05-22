# Workspace v2 (manifest + declarative tools)

## Layout

| File | Purpose |
|------|---------|
| `00_manifest.yaml` | Tenant id, paths, knowledge inject mode |
| `01_core/system_prompt.md` | Agent instructions |
| `02_knowledge/faq/master_faq.md` | Canonical FAQ (compiled to `compiled/kb_chunks.jsonl`) |
| `03_tools/tools.yaml` | Enabled builtins for the ReAct loop |
| `04_channels/handover.yaml` | Office hours, handover keywords, media policy, clarify fallbacks |
| `05_copy/chat_copy.yaml` | Handover, footer, resume copy |
| `settings.yaml` | Non-secret defaults |
| `.env` | API keys and integration secrets |

Legacy `00_manifest.md` frontmatter is still read if YAML is missing.

## CLI

```bash
python3 tools/kai init --workspace agent_workspace
python3 tools/kai doctor
python3 tools/kai doctor --ping-llm
python3 tools/kai compile
```

## Knowledge inject modes

- `full_context` — entire FAQ in system prompt (Kommu default)
- `retrieval_first` — prompt tells model to use `search_faq` (generic template default)

## Channels (`04_channels/handover.yaml`)

Controls **behavior** (not all user-visible strings): office hours, `LA` / resume keywords, blocked WhatsApp media types, and agent clarify fallbacks. Copy strings remain in `05_copy/chat_copy.yaml`.

## Tools

Each entry in `03_tools/tools.yaml`:

```yaml
- id: search_faq
  builtin: search_faq
  enabled: true
```

`builtin` must exist in `kai/support_runtime/tools/catalog.py` (legacy ids are aliased, e.g. `search_kommu_support` → `search_official_site`).

**Profiles:** set `active_profile: minimal` and define `profiles:` — leave `tools: []` to expand the list.

**Plugins:** `plugin: smartserva_visitor_pass` runs `agent_workspace/03_tools/plugins/<id>/main.py` or `kai/integrations/...` fallback.

## API health

- `GET /health` — liveness
- `GET /ready` — workspace validation summary (tenant, chunks, tools, errors)

Set `KAI_STRICT_STARTUP=1` to abort boot when `kai doctor` would report errors.
