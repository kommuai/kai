from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from fastapi import HTTPException


def _load_workspace_yaml(workspace_home: Path) -> dict[str, Any]:
    p = workspace_home / "workspace.yaml"
    if not p.is_file():
        raise HTTPException(status_code=404, detail=f"workspace.yaml not found at {p}")
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8", errors="replace")) or {}
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid workspace.yaml: {exc}") from exc
    if not isinstance(data, dict):
        raise HTTPException(status_code=422, detail="Invalid workspace.yaml format")
    return data


def _save_workspace_yaml(workspace_home: Path, data: dict[str, Any]) -> None:
    p = workspace_home / "workspace.yaml"
    p.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def set_profile_skill_enabled(workspace_home: Path, skill_id: str, enabled: bool) -> None:
    data = _load_workspace_yaml(workspace_home)
    tp = data.get("tools_profile")
    if not isinstance(tp, dict):
        tp = {}
        data["tools_profile"] = tp
    overrides = tp.get("profile_overrides")
    if not isinstance(overrides, dict):
        overrides = {}
        tp["profile_overrides"] = overrides

    ov = overrides.get(skill_id)
    if not isinstance(ov, dict):
        ov = {}
        overrides[skill_id] = ov
    ov["enabled"] = bool(enabled)

    _save_workspace_yaml(workspace_home, data)


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        meta = {}
    if not isinstance(meta, dict):
        meta = {}
    body = parts[2].lstrip("\n")
    return meta, body


def set_document_skill_enabled(workspace_home: Path, rel_path: str, enabled: bool) -> None:
    rel = (rel_path or "").strip().lstrip("/")
    if not rel:
        raise HTTPException(status_code=400, detail="Missing skill document path")
    p = (workspace_home / rel).resolve()
    try:
        p.relative_to(workspace_home.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Skill path must be under workspace") from exc
    if not p.is_file():
        raise HTTPException(status_code=404, detail=f"Skill file not found: {rel}")

    text = p.read_text(encoding="utf-8", errors="replace")
    meta, body = _parse_frontmatter(text)
    meta["enabled"] = bool(enabled)
    new_text = "---\n" + yaml.safe_dump(meta, sort_keys=False, allow_unicode=True).strip() + "\n---\n\n" + body.lstrip("\n")
    p.write_text(new_text, encoding="utf-8")

