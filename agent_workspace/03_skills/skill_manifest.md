---
description: Human-readable overview of Kai skills (v2 router).
---

# Skills

Each subdirectory under `03_skills/` contains:

- `skill.md` — YAML frontmatter (`id`, `version`, `enabled`, `handler_class`, `timeout_ms`, `retry_count`, `permissions`) plus optional markdown notes.
- `handler.py` — Python module defining the class named in `handler_class` (loaded via `importlib`).

The v2 API loads enabled skills from these folders via `WorkspaceSkillRegistry` and `build_workspace_skill`.
