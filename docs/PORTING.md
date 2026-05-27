# Porting a new business

Kai is **tenant-agnostic at runtime**. Behavior comes from `KAI_HOME`, not engine code.

## Steps

1. **Install engine** — `./scripts/install.sh` or Docker
2. **Init home** — `kai workspace init`
3. **Author tenant pack** — copy `templates/workspace/generic/` or fork an existing pack
4. **Install pack** — `kai pack install ./my-tenant-pack`
5. **Configure secrets** — edit `~/.kai/.env`
6. **Validate** — `kai doctor` and `kai compile`

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
kai pack install ./my-tenant-pack [--force]
kai pack export --output my-tenant.tgz
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

Kommu ships in a **separate repo**: `kai-tenant-kommu` (install with `kai pack install`).

## API surface (unchanged)

- `POST /v2/agent/message` — primary chat
- `GET /health`, `GET /ready` — probes

One process = one `KAI_HOME` = one tenant.
