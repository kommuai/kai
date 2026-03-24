"""Load skill manifests from agent_workspace/03_skills/*/skill.md (YAML frontmatter)."""
from __future__ import annotations

import logging
from pathlib import Path

from core.skills.registry import SkillManifest

log = logging.getLogger("kai.workspace_skills")

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


class WorkspaceSkillRegistry:
    def __init__(self, skills_root: str | Path):
        self.skills_root = Path(skills_root)
        self._manifests: dict[str, SkillManifest] = {}

    def load(self) -> dict[str, SkillManifest]:
        self._manifests = {}
        if yaml is None:
            log.warning("PyYAML missing; workspace skills not loaded")
            return self._manifests
        if not self.skills_root.is_dir():
            log.warning("Workspace skills root missing: %s", self.skills_root)
            return self._manifests

        for skill_dir in sorted(self.skills_root.iterdir()):
            if not skill_dir.is_dir():
                continue
            sm_path = skill_dir / "skill.md"
            if not sm_path.is_file():
                continue
            raw = sm_path.read_text(encoding="utf-8")
            if not raw.lstrip().startswith("---"):
                continue
            end = raw.find("\n---", 3)
            if end == -1:
                continue
            fm_raw = raw[3:end]
            try:
                data = yaml.safe_load(fm_raw) or {}
            except Exception as exc:  # noqa: BLE001
                log.warning("Bad frontmatter in %s: %s", sm_path, exc)
                continue
            if not isinstance(data, dict):
                continue
            sid = data.get("id")
            if not sid:
                continue
            handler_class = (data.get("handler_class") or "").strip()
            if not handler_class:
                log.warning("skill.md missing handler_class for id=%s (%s)", sid, sm_path)
                continue
            perms = data.get("permissions") or []
            if not isinstance(perms, list):
                perms = []
            manifest = SkillManifest(
                skill_id=str(sid),
                version=str(data.get("version", "0.1.0")),
                enabled=bool(data.get("enabled", True)),
                handler_class=handler_class,
                timeout_ms=int(data.get("timeout_ms", 8000)),
                retry_count=int(data.get("retry_count", 1)),
                permissions=[str(p) for p in perms],
            )
            self._manifests[manifest.skill_id] = manifest
        return self._manifests

    def enabled_skills(self) -> list[SkillManifest]:
        return [m for m in self._manifests.values() if m.enabled]

    def as_dict(self) -> dict:
        return {sid: m.as_dict() for sid, m in self._manifests.items()}
