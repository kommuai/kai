"""Load skill classes from agent_workspace/03_skills/<id>/handler.py (importlib)."""
from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from types import ModuleType

from config import AGENT_WORKSPACE
from core.skills.registry import SkillManifest

log = logging.getLogger("kai.workspace_factory")


def _module_name(skill_id: str) -> str:
    return f"kai_ws_skill.{skill_id}"


def load_handler_class(skill_id: str, class_name: str) -> type:
    path = Path(AGENT_WORKSPACE) / "03_skills" / skill_id / "handler.py"
    if not path.is_file():
        raise FileNotFoundError(f"Missing handler: {path}")
    mod_name = _module_name(skill_id)
    if mod_name in sys.modules:
        mod = sys.modules[mod_name]
    else:
        spec = importlib.util.spec_from_file_location(mod_name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load spec for {path}")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = mod
        spec.loader.exec_module(mod)
    cls = getattr(mod, class_name, None)
    if cls is None:
        raise AttributeError(f"{mod_name} has no class {class_name}")
    return cls


def reload_handler_module(skill_id: str) -> None:
    """Drop cached module so the next load re-reads handler.py from disk."""
    mod_name = _module_name(skill_id)
    sys.modules.pop(mod_name, None)


def build_workspace_skill(manifest: SkillManifest):
    try:
        klass = load_handler_class(manifest.skill_id, manifest.handler_class)
        return klass()
    except Exception as exc:  # noqa: BLE001
        log.exception("Failed to load skill %s: %s", manifest.skill_id, exc)
        raise


def get_workspace_skill_registry():
    """Load manifests from agent_workspace/03_skills (cached instance not used — call load() each time if needed)."""
    from core.skills.workspace_registry import WorkspaceSkillRegistry

    reg = WorkspaceSkillRegistry(Path(AGENT_WORKSPACE) / "03_skills")
    reg.load()
    return reg


def load_workspace_skills() -> list:
    reg = get_workspace_skill_registry()
    return [build_workspace_skill(m) for m in reg.enabled_skills()]
