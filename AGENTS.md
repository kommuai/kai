# AGENTS Guide

This repository supports both human chat and machine-agent integrations.

## Architecture Boundaries

- `api/v2/`: all HTTP chat and admin routes (`POST /agent/message`, `POST /v2/agent/message`, `/admin/*`, `/v2/agent/query`, etc.).
- `core/`: routing, policy, registry, authz, provenance primitives.
- `agent_workspace/03_skills/<id>/`: pluggable v2 skills (`skill.md` + `handler.py`).
- `agent_workspace/04_context/context_registry.yaml`: enable/disable context groups.
- `workers/`: async execution for heavy capabilities.

## Safe Edit Zones

- Add/modify skills under `agent_workspace/03_skills/<id>/` (`python tools/new_skill.py --id my_skill`).
- Add contexts via `python tools/new_context.py --id my_context` or edit `context_registry.yaml`.
- Add policy rules in `core/policy/`.

## Restricted Edits (Require Caution)

- Do not break `POST /agent/message` or `POST /v2/agent/message` payload or response envelope (n8n/WhatsApp).
- Keep `pre_router` + `main_conversation` ordering correct so handover/frozen runs before skills.
- Keep n8n compatibility for A2A endpoints that use service keys.

## Before Proposing a Change

1. Ensure `skill.md` frontmatter and `context_registry.yaml` are valid YAML.
2. Run Python compile checks.
3. Ensure contract tests under `tests/` pass.

## Skill Contract Summary

- `can_handle(request, context_meta) -> float`
- `execute(request, context_bundle, budget) -> CapabilityResult`
- `degrade(reason) -> CapabilityResult`

## Context Contract Summary

- `refresh()`
- `retrieve(query, filters, top_k)`
- `health()`

