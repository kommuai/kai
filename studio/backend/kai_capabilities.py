"""Resolve tenant skills for Studio (profile actions + skills/ docs)."""

from __future__ import annotations



from pathlib import Path

from typing import Any



import yaml





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

    body = parts[2].strip()

    return meta, body





def _first_paragraph(body: str) -> str:

    for block in body.split("\n\n"):

        line = block.strip().lstrip("#").strip()

        if line and not line.startswith("---"):

            return line[:500]

    return ""





def _list_document_skills(workspace_home: Path) -> list[dict[str, Any]]:

    skills_dir = workspace_home / "skills"

    if not skills_dir.is_dir():

        return []



    items: list[dict[str, Any]] = []

    for child in sorted(skills_dir.iterdir()):

        if child.name.startswith("."):

            continue

        if child.is_dir():

            skill_md = child / "skill.md"

            if not skill_md.is_file():

                continue

            text = skill_md.read_text(encoding="utf-8", errors="replace")

            meta, body = _parse_frontmatter(text)

            skill_id = str(meta.get("id") or child.name).strip()

            desc = str(meta.get("description") or "").strip() or _first_paragraph(body)

            enabled = meta.get("enabled", True)

            if isinstance(enabled, str):

                enabled = enabled.strip().lower() not in {"0", "false", "no", "off"}

            items.append(

                {

                    "id": skill_id,

                    "description": desc or "Procedural skill (see skill.md for details).",

                    "enabled": bool(enabled),

                    "source": "document",

                    "path": str(skill_md.relative_to(workspace_home)),

                    "builtin": None,

                    "canonical_builtin": None,

                    "plugin": None,

                }

            )

        elif child.suffix.lower() == ".md" and child.name.lower() != "readme.md":

            text = child.read_text(encoding="utf-8", errors="replace")

            meta, body = _parse_frontmatter(text)

            skill_id = str(meta.get("id") or child.stem).strip()

            desc = str(meta.get("description") or "").strip() or _first_paragraph(body)

            items.append(

                {

                    "id": skill_id,

                    "description": desc or "Skill documentation file.",

                    "enabled": True,

                    "source": "document",

                    "path": str(child.relative_to(workspace_home)),

                    "builtin": None,

                    "canonical_builtin": None,

                    "plugin": None,

                }

            )

    return items





def _list_profile_skills(workspace_home: Path) -> tuple[list[dict[str, Any]], str]:
    """Agent actions from this workspace's `workspace.yaml` tools profile.

    Important: we intentionally parse the tenant's `workspace.yaml` directly instead of using
    `kai.workspace.tools_config` because that module is optimized around a single active `KAI_HOME`
    and caches settings across calls. Studio needs per-tenant isolation.
    """

    from kai.support_runtime.tools.catalog import builtin_catalog, resolve_builtin_id

    workspace_yaml = workspace_home / "workspace.yaml"
    if not workspace_yaml.is_file():
        return [], "default"

    try:
        data = yaml.safe_load(workspace_yaml.read_text(encoding="utf-8", errors="replace")) or {}
    except yaml.YAMLError:
        return [], "default"
    if not isinstance(data, dict):
        return [], "default"

    raw: dict[str, Any] = {}
    for key in ("tools_profile", "tools"):
        block = data.get(key)
        if isinstance(block, dict) and (
            "active_profile" in block or "profiles" in block or "tools" in block or "profile_overrides" in block
        ):
            raw = block
            break

    active = str(raw.get("active_profile") or raw.get("profile") or "").strip() or "default"
    profiles = raw.get("profiles") if isinstance(raw.get("profiles"), dict) else {}
    overrides = raw.get("profile_overrides") if isinstance(raw.get("profile_overrides"), dict) else {}

    tools_list = raw.get("tools")
    if not isinstance(tools_list, list):
        tools_list = []

    if not tools_list and active and profiles:
        ids = profiles.get(active)
        if isinstance(ids, list):
            tools_list = []
            for i in [str(x).strip() for x in ids if str(x).strip()]:
                canonical = resolve_builtin_id(i)
                item: dict[str, Any] = {"id": i, "builtin": canonical, "enabled": True}
                ov = overrides.get(i) or overrides.get(canonical)
                if isinstance(ov, dict):
                    item.update(ov)
                tools_list.append(item)

    catalog = builtin_catalog()
    items: list[dict[str, Any]] = []
    for item in tools_list:
        if isinstance(item, str):
            tool_id = item.strip()
            if not tool_id:
                continue
            canonical = resolve_builtin_id(tool_id)
            desc = catalog.get(canonical).description if canonical in catalog else "No description available."
            items.append(
                {
                    "id": tool_id,
                    "description": desc,
                    "enabled": True,
                    "source": "profile",
                    "path": None,
                    "builtin": tool_id,
                    "canonical_builtin": canonical,
                    "plugin": None,
                }
            )
            continue

        if not isinstance(item, dict):
            continue

        tool_id = str(item.get("id") or item.get("name") or "").strip()
        if not tool_id:
            continue
        builtin = str(item.get("builtin") or tool_id).strip()
        canonical = resolve_builtin_id(builtin)
        enabled = item.get("enabled", True)
        if isinstance(enabled, str):
            enabled = enabled.strip().lower() not in {"0", "false", "no", "off"}
        desc = str(item.get("description") or "").strip()
        if not desc and canonical in catalog:
            desc = catalog[canonical].description
        plugin = str(item.get("plugin") or "").strip() or None
        if not desc and plugin:
            desc = f"Custom plugin: {plugin}"
        items.append(
            {
                "id": tool_id,
                "description": desc or "No description available.",
                "enabled": bool(enabled),
                "source": "profile",
                "path": None,
                "builtin": builtin,
                "canonical_builtin": canonical,
                "plugin": plugin,
            }
        )

    # Show enabled first, but keep stable ordering within each group.
    items.sort(key=lambda x: (not x.get("enabled", True), str(x.get("id", ""))))
    return items, active





def get_capabilities(workspace_home: str | Path) -> dict[str, Any]:

    home = Path(workspace_home).resolve()

    if not home.is_dir():

        raise FileNotFoundError(f"Workspace not found: {home}")

    profile_skills, active_profile = _list_profile_skills(home)

    document_skills = _list_document_skills(home)

    return {

        "active_profile": active_profile,

        "skills": profile_skills + document_skills,

    }


