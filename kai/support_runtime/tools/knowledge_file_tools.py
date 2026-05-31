"""Read-only knowledge file tools, scoped to tenant KAI_HOME/knowledge/.

All paths are normalised and validated to stay inside allowed roots before
any file is opened.  The tools never write or execute; they are purely
read-only filesystem helpers.

Tenant opts in by listing the tool ids in workspace.yaml tools_profile.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any


# --------------------------------------------------------------------------- #
# Path safety
# --------------------------------------------------------------------------- #

def _knowledge_roots(extra_roots: list[str] | None = None) -> list[Path]:
    """Return the list of allowed read roots for the current tenant."""
    from kai.settings import get_settings

    base = get_settings().kai_home / "knowledge"
    roots: list[Path] = [base.resolve()]
    for r in extra_roots or []:
        p = Path(r).resolve()
        if p.is_dir():
            roots.append(p)
    return roots


def _safe_resolve(rel_or_abs: str, extra_roots: list[str] | None = None) -> Path | None:
    """Resolve a path and verify it is inside an allowed root.

    Returns the resolved Path, or None when the path is denied.
    """
    raw = (rel_or_abs or "").strip()
    if not raw:
        return None

    roots = _knowledge_roots(extra_roots)

    # Try each root for relative paths; also accept absolute paths that fall
    # inside a root.
    candidates: list[Path] = []
    p = Path(raw)
    if p.is_absolute():
        candidates.append(p.resolve())
    else:
        for root in roots:
            candidates.append((root / p).resolve())

    for resolved in candidates:
        for root in roots:
            try:
                resolved.relative_to(root)
                return resolved
            except ValueError:
                continue

    return None  # traversal denied


# --------------------------------------------------------------------------- #
# Tool implementations (stateless; one function per tool)
# --------------------------------------------------------------------------- #

def list_knowledge_files(
    glob: str = "**/*.md",
    extra_roots: list[str] | None = None,
) -> dict[str, Any]:
    """List files matching a glob pattern inside knowledge roots."""
    roots = _knowledge_roots(extra_roots)
    matches: list[str] = []
    for root in roots:
        if not root.is_dir():
            continue
        for p in root.glob(glob or "**/*.md"):
            if p.is_file():
                try:
                    rel = str(p.relative_to(root))
                except ValueError:
                    rel = str(p)
                matches.append(rel)
    matches.sort()
    return {"ok": True, "files": matches, "count": len(matches)}


def read_knowledge_lines(
    path: str,
    start: int = 1,
    end: int = 50,
    extra_roots: list[str] | None = None,
) -> dict[str, Any]:
    """Read a line range from a knowledge file (1-indexed, inclusive)."""
    resolved = _safe_resolve(path, extra_roots)
    if resolved is None:
        return {"ok": False, "error": "access_denied", "path": path}
    if not resolved.is_file():
        return {"ok": False, "error": "file_not_found", "path": path}

    start = max(1, int(start or 1))
    end = max(start, int(end or start + 49))
    if end - start > 500:
        end = start + 500  # hard cap to prevent huge reads

    lines = resolved.read_text(encoding="utf-8", errors="replace").splitlines()
    total = len(lines)
    sliced = lines[start - 1 : end]
    return {
        "ok": True,
        "path": path,
        "start": start,
        "end": min(end, total),
        "total_lines": total,
        "content": "\n".join(sliced),
    }


def grep_knowledge(
    pattern: str,
    glob: str = "**/*.md",
    literal: bool = True,
    max_hits: int = 20,
    extra_roots: list[str] | None = None,
) -> dict[str, Any]:
    """Search for a string or regex pattern across knowledge files."""
    if not pattern:
        return {"ok": False, "error": "missing_pattern"}

    roots = _knowledge_roots(extra_roots)
    flags = re.IGNORECASE
    try:
        rx = re.compile(re.escape(pattern) if literal else pattern, flags)
    except re.error as exc:
        return {"ok": False, "error": f"invalid_pattern:{exc}"}

    hits: list[dict[str, Any]] = []
    for root in roots:
        if not root.is_dir():
            continue
        for p in root.glob(glob or "**/*.md"):
            if not p.is_file():
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                if rx.search(line):
                    try:
                        rel = str(p.relative_to(root))
                    except ValueError:
                        rel = str(p)
                    hits.append({"file": rel, "line_number": lineno, "line": line.rstrip()})
                    if len(hits) >= max_hits:
                        return {"ok": True, "hits": hits, "truncated": True, "count": len(hits)}
    return {"ok": True, "hits": hits, "truncated": False, "count": len(hits)}


def get_file_outline(
    path: str,
    extra_roots: list[str] | None = None,
) -> dict[str, Any]:
    """Return the Markdown heading tree for a knowledge file."""
    resolved = _safe_resolve(path, extra_roots)
    if resolved is None:
        return {"ok": False, "error": "access_denied", "path": path}
    if not resolved.is_file():
        return {"ok": False, "error": "file_not_found", "path": path}

    headings: list[dict[str, Any]] = []
    for lineno, line in enumerate(
        resolved.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
    ):
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            headings.append({"level": len(m.group(1)), "title": m.group(2).strip(), "line": lineno})
    return {"ok": True, "path": path, "headings": headings, "count": len(headings)}


def read_knowledge_section(
    path: str,
    heading: str,
    extra_roots: list[str] | None = None,
) -> dict[str, Any]:
    """Return the text under a specific Markdown heading (until the next same-level heading)."""
    resolved = _safe_resolve(path, extra_roots)
    if resolved is None:
        return {"ok": False, "error": "access_denied", "path": path}
    if not resolved.is_file():
        return {"ok": False, "error": "file_not_found", "path": path}
    if not heading:
        return {"ok": False, "error": "missing_heading"}

    lines = resolved.read_text(encoding="utf-8", errors="replace").splitlines()
    heading_lower = heading.strip().lower()

    start_line: int | None = None
    heading_level: int | None = None

    for lineno, line in enumerate(lines):
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m and m.group(2).strip().lower() == heading_lower:
            start_line = lineno
            heading_level = len(m.group(1))
            break

    if start_line is None:
        return {"ok": False, "error": "heading_not_found", "path": path, "heading": heading}

    body_lines: list[str] = []
    for line in lines[start_line + 1 :]:
        m = re.match(r"^(#{1,6})\s+", line)
        if m and len(m.group(1)) <= heading_level:
            break
        body_lines.append(line)

    return {
        "ok": True,
        "path": path,
        "heading": heading,
        "start_line": start_line + 1,
        "content": "\n".join(body_lines).strip(),
    }


def extract_frontmatter(
    path: str,
    extra_roots: list[str] | None = None,
) -> dict[str, Any]:
    """Extract YAML front matter from a knowledge file."""
    resolved = _safe_resolve(path, extra_roots)
    if resolved is None:
        return {"ok": False, "error": "access_denied", "path": path}
    if not resolved.is_file():
        return {"ok": False, "error": "file_not_found", "path": path}

    text = resolved.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return {"ok": True, "path": path, "frontmatter": {}, "has_frontmatter": False}

    end = text.find("\n---", 3)
    if end < 0:
        return {"ok": True, "path": path, "frontmatter": {}, "has_frontmatter": False}

    block = text[3:end].strip()
    try:
        import yaml  # type: ignore[import]
        data = yaml.safe_load(block) or {}
        fm = data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001
        fm = {}

    return {"ok": True, "path": path, "frontmatter": fm, "has_frontmatter": True}
