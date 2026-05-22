# Context Providers

Context providers supply retrievable evidence for capabilities.

## Contract

- `refresh()`
- `retrieve(query, filters, top_k)`
- `health()`

## Registry

- **Source:** `agent_workspace/04_context/context_registry.yaml` — list under `contexts:` with `id`, `enabled`, `kind`, `config`.
- If the file is missing or PyYAML is unavailable, the registry loads nothing and logs a warning (no JSON fallback).
- Production chat does **not** load a Python context registry. Edit `context_registry.yaml` for documentation/scaffolding; `tools/new_context.py` appends entries. Path: `agent_workspace/04_context/context_registry.yaml` (see `config.CONTEXT_REGISTRY_YAML`).
