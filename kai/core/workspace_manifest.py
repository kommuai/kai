"""Load optional metadata from agent_workspace/00_manifest.md (YAML frontmatter)."""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

log = logging.getLogger("kai.workspace_manifest")

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


def parse_frontmatter_markdown(path: Path) -> tuple[dict[str, Any], str]:
    """Return (frontmatter_dict, body_markdown). Empty dict if no frontmatter."""
    if not path.is_file():
        return {}, ""
    raw = path.read_text(encoding="utf-8")
    if not raw.lstrip().startswith("---"):
        return {}, raw
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", raw, re.DOTALL)
    if not m:
        return {}, raw
    body = raw[m.end() :]
    if yaml is None:
        log.warning("PyYAML not installed; skipping manifest frontmatter parse")
        return {}, body
    try:
        data = yaml.safe_load(m.group(1)) or {}
        if not isinstance(data, dict):
            return {}, body
        return data, body
    except Exception as exc:  # noqa: BLE001
        log.warning("Manifest frontmatter parse failed: %s", exc)
        return {}, body


def log_session_store_hint(manifest_path: Path) -> None:
    """Log where SQLite session DB is configured (from manifest if present)."""
    meta, _ = parse_frontmatter_markdown(manifest_path)
    ss = meta.get("session_store")
    if isinstance(ss, dict):
        log.info(
            "[workspace] session_store backend=%s env=%s docker_path=%s",
            ss.get("backend"),
            ss.get("env_path_var"),
            ss.get("docker_container_path"),
        )
