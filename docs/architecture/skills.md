# Skills Architecture

Skills are capability modules loaded from the agent workspace and selected by router policy.

## Contract

- `can_handle(request, context_meta) -> float`
- `execute(request, context_bundle, budget) -> CapabilityResult`
- `degrade(reason) -> CapabilityResult`

## Workspace activation

- **Source:** `agent_workspace/03_skills/<skill_id>/skill.md` with YAML frontmatter (`id`, `version`, `enabled`, `handler_class`, `timeout_ms`, `retry_count`, `permissions`) plus optional markdown notes.
- **Implementation:** `agent_workspace/03_skills/<skill_id>/handler.py` — Python module loaded with `importlib` (the folder name `03_skills` is not a dotted import path).
- `core/skills/workspace_registry.py` parses `skill.md`; `core/skills/workspace_factory.py` loads `handler_class` from `handler.py` and instantiates it for the v2 router.

## Current skills

- `legacy_rag`
- `legacy_warranty`
- `repo_reader`
- `image_diag`
- `video_diag`
