# Policies

Policy concerns are centralized in `core/policy/`.

## Tool Governance

- unified execution wrapper for retries and audit logs
- per-skill timeout and retry limits from `skill.md` frontmatter
- route-level fallback requirements

## Security

- service-to-service auth for A2A endpoints via scoped keys
- machine endpoint scopes:
  - `public_info.read`
  - `repo.read`
  - `media.read`

