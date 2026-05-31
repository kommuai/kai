"""Deterministic plugin contract for agent tool calls (CLI args + JSON on stdout)."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

# Patterns that break the runner (stdin JSON plugins).
_FORBIDDEN_PATTERNS = (
    re.compile(r"json\.load\s*\(\s*sys\.stdin"),
    re.compile(r"input\s*\(\s*\)"),
)

_REQUIRED_PATTERNS = (
    re.compile(r"argparse|ArgumentParser"),
    re.compile(r"json\.dumps"),
    re.compile(r'"ok"\s*:\s*(True|False)'),
)


def validate_plugin_source(source: str, *, plugin_id: str = "") -> list[str]:
    """Return human-readable validation errors (empty list = OK)."""
    errors: list[str] = []
    label = plugin_id or "plugin"
    if not source.strip():
        return [f"{label}: empty script"]
    for pat in _FORBIDDEN_PATTERNS:
        if pat.search(source):
            errors.append(f"{label}: must not use stdin JSON contract (use argparse + stdout JSON)")
    for pat in _REQUIRED_PATTERNS:
        if not pat.search(source):
            errors.append(f"{label}: missing required pattern {pat.pattern}")
    if "__main__" not in source:
        errors.append(f"{label}: missing if __name__ == '__main__' guard")
    try:
        ast.parse(source)
    except SyntaxError as exc:
        errors.append(f"{label}: syntax error: {exc}")
    return errors


def validate_plugin_file(path: Path, *, plugin_id: str = "") -> list[str]:
    if not path.is_file():
        return [f"{plugin_id or path}: file not found"]
    return validate_plugin_source(path.read_text(encoding="utf-8", errors="replace"), plugin_id=plugin_id or path.parent.name)


def normalize_tool_result(payload: dict[str, Any]) -> dict[str, Any]:
    """Ensure tool/plugin results expose ok + error consistently."""
    if not isinstance(payload, dict):
        return {"ok": False, "error": "invalid_tool_result:not_object"}
    if "ok" not in payload:
        return {"ok": False, "error": "invalid_tool_result:missing_ok", **payload}
    ok = bool(payload.get("ok"))
    out = dict(payload)
    out["ok"] = ok
    if not ok and not str(out.get("error") or "").strip():
        out["error"] = "tool_failed:unknown"
    return out


def tool_failure_observation_message(tool_name: str, result: dict[str, Any]) -> str:
    err = str(result.get("error") or "unknown_error").strip()
    return (
        f"Tool `{tool_name}` failed (ok: false).\n"
        f"Exact error: {err}\n\n"
        "You MUST either retry with corrected args, call a different tool, or give a final answer "
        "that quotes this exact error. Do NOT invent outage messages or alternate reasons."
    )
