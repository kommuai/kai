# Tenant packs

The **engine** is generic Python under `kai/`. Each business ships a **workspace pack** (no code required).

## Kommu (default in this repo)

See also [`packs/kommu/README.md`](kommu/README.md).

Uses `agent_workspace/` at repo root:

- `00_manifest.yaml` — tenant id, FAQ inject mode
- `03_tools/tools.yaml` — `active_profile: kommu` + `profile_overrides` (URLs, GitHub repo, plugins)
- `03_tools/plugins/smartserva_visitor_pass/main.py` — visitor pass plugin
- `04_channels/handover.yaml` — office hours, LA/resume, fallbacks

## New business

```bash
python3 tools/kai init --workspace ./agent_workspace
```

Edit FAQ and set `knowledge.inject_mode: retrieval_first` in `00_manifest.yaml`.

Full checklist: [docs/PORTING.md](../docs/PORTING.md). Run `python3 -m kai.cli port-check` after editing tools.
