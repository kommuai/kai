import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

log = logging.getLogger("kai.context_registry")


@dataclass
class ContextManifest:
    context_id: str
    enabled: bool
    kind: str
    config: dict[str, Any]


class ContextRegistry:
    """Load context manifests from agent_workspace/04_context/context_registry.yaml only."""

    def __init__(self, registry_yaml: str | Path | None = None):
        from config import CONTEXT_REGISTRY_YAML

        self.yaml_path = Path(registry_yaml or CONTEXT_REGISTRY_YAML)
        self._manifests: dict[str, ContextManifest] = {}

    def load(self) -> dict[str, ContextManifest]:
        self._manifests = {}
        if yaml is None:
            log.warning("PyYAML missing; context registry empty (%s not read)", self.yaml_path)
            return self._manifests
        if not self.yaml_path.is_file():
            log.warning("Context registry YAML missing: %s", self.yaml_path)
            return self._manifests
        try:
            doc = yaml.safe_load(self.yaml_path.read_text(encoding="utf-8")) or {}
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to parse %s: %s", self.yaml_path, exc)
            return self._manifests
        items = doc.get("contexts") if isinstance(doc, dict) else None
        if not isinstance(items, list):
            return self._manifests
        for data in items:
            if not isinstance(data, dict) or "id" not in data:
                continue
            manifest = ContextManifest(
                context_id=data["id"],
                enabled=bool(data.get("enabled", True)),
                kind=data.get("kind", "generic"),
                config=data.get("config") or {},
            )
            self._manifests[manifest.context_id] = manifest
        return self._manifests

    def enabled_contexts(self) -> list[ContextManifest]:
        return [m for m in self._manifests.values() if m.enabled]
