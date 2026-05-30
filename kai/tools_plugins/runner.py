from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from kai.settings import get_settings
from kai.tools_plugins.contract import normalize_tool_result, validate_plugin_file


def _kai_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _plugin_subprocess_env() -> dict[str, str]:
    """Ensure tenant plugins can import the `kai` package."""
    env = os.environ.copy()
    repo = str(_kai_repo_root())
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join([repo, existing]) if existing else repo
    return env


def _cli_flag(key: str, params: dict[str, Any]) -> str:
    aliases = params.get("arg_aliases")
    if isinstance(aliases, dict):
        mapped = aliases.get(key)
        if mapped:
            return str(mapped).strip().replace("_", "-")
    return key.replace("_", "-")


def resolve_plugin_script(plugin_id: str, params: dict[str, Any]) -> Path | None:
    explicit = str(params.get("script") or params.get("path") or os.getenv(f"KAI_PLUGIN_{plugin_id.upper()}_PATH", "")).strip()
    if explicit and Path(explicit).is_file():
        return Path(explicit)

    from kai.workspace.manifest import load_workspace_manifest

    ws = get_settings().kai_home
    plugins_dir = load_workspace_manifest().paths.tools_plugins_dir
    candidates = [
        ws / plugins_dir / plugin_id / "main.py",
        ws / plugins_dir / f"{plugin_id}.py",
    ]
    return next((p for p in candidates if p.is_file()), None)


def run_plugin_tool(
    plugin_id: str,
    params: dict[str, Any],
    args: dict[str, Any],
    *,
    timeout_sec: int | None = None,
) -> dict[str, Any]:
    script = resolve_plugin_script(plugin_id, params)
    if not script:
        return {"ok": False, "error": f"missing_plugin_script:{plugin_id}"}

    timeout = timeout_sec or int(params.get("timeout_seconds") or os.getenv("KAI_PLUGIN_TIMEOUT_SECONDS", "180"))
    python = os.getenv("KAI_PYTHON") or sys.executable
    cmd = [python, str(script)]
    for key, value in (args or {}).items():
        if value is None or value == "":
            continue
        cmd.extend([f"--{_cli_flag(key, params)}", str(value)])

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=_plugin_subprocess_env(),
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"plugin_timeout:{plugin_id}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"plugin_exec_failed:{exc}"}

    merged = "\n".join(x for x in [(proc.stdout or "").strip(), (proc.stderr or "").strip()] if x)
    m = re.search(r"\{.*\}", merged, flags=re.S)
    payload: dict[str, Any] = {}
    if m:
        try:
            obj = json.loads(m.group(0))
            if isinstance(obj, dict):
                payload = obj
        except Exception:
            payload = {}

    if proc.returncode != 0:
        return normalize_tool_result(
            {
                "ok": False,
                "error": payload.get("error") if payload else f"plugin_failed:{plugin_id}",
                "stdout": (proc.stdout or "")[:500],
                "stderr": (proc.stderr or "")[:500],
                "exit_code": proc.returncode,
            }
        )
    if payload:
        return normalize_tool_result(payload)
    return normalize_tool_result(
        {
            "ok": False,
            "error": f"plugin_invalid_output:{plugin_id}",
            "stdout": (proc.stdout or "")[:500],
        }
    )


def validate_plugin_at_path(script: Path, *, plugin_id: str = "") -> list[str]:
    return validate_plugin_file(script, plugin_id=plugin_id)
