from dataclasses import dataclass
from typing import Any


@dataclass
class SkillManifest:
    skill_id: str
    version: str
    enabled: bool
    """Class name defined in agent_workspace/03_skills/<skill_id>/handler.py."""
    handler_class: str
    timeout_ms: int = 8000
    retry_count: int = 1
    permissions: list[str] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "enabled": self.enabled,
            "handler_class": self.handler_class,
            "timeout_ms": self.timeout_ms,
            "retry_count": self.retry_count,
            "permissions": self.permissions or [],
        }
