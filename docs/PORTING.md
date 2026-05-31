# Porting a new business

Shadou is **tenant-agnostic at runtime**. Behavior comes from `SHADOU_HOME`, not engine code.

## Steps

1. **Install engine** — `./scripts/install.sh` or Docker
2. **Init home** — `shadou workspace init`
3. **Author tenant pack** — copy `templates/workspace/generic/` or fork an existing pack
4. **Install pack** — `shadou pack install ./my-tenant-pack`
5. **Configure secrets** — edit `~/.shadou/.env`
6. **Validate** — `shadou doctor` and `shadou compile`

## Tenant pack structure

```
my-tenant-pack/
├── pack.yaml              # metadata (optional)
├── workspace.yaml         # tenant id, tools_profile, channels, copy
├── system_prompt.md
├── knowledge/master_faq.md
└── tools/plugins/<id>/main.py
```

## Pack commands

```bash
shadou pack install ./my-tenant-pack [--force]
shadou pack export --output my-tenant.tgz
```

Rules: pack install skips existing files unless `--force`. Runtime dirs `compiled/` and `data/` are not overwritten from packs.

## Tool profiles

Define `tools_profile` in `workspace.yaml`:

```yaml
tools_profile:
  active_profile: minimal
  profiles:
    minimal: [search_faq, search_session_memory, escalate_to_human]
  profile_overrides: {}
  tools: []
```

Legacy tool ids (`search_kommu_support`, etc.) map to generic builtins via `BUILTIN_ALIASES`.

## Reference tenant

Kommu ships in a **separate repo**: `shadou-tenant-kommu` (install with `shadou pack install`).

## API surface (unchanged)

- `POST /v2/agent/message` — primary chat
- `GET /health`, `GET /ready` — probes

One process = one `SHADOU_HOME` = one tenant.
