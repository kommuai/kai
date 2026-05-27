from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from kai.settings import get_settings


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
    cmd = ["python3", str(script)]
    for key, value in (args or {}).items():
        if value is None or value == "":
            continue
        cmd.extend([f"--{key.replace('_', '-')}", str(value)])

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
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
        return {
            "ok": False,
            "error": payload.get("error") if payload else f"plugin_failed:{plugin_id}",
            "stdout": (proc.stdout or "")[:500],
        }
    if payload:
        return payload
    return {"ok": False, "error": f"plugin_invalid_output:{plugin_id}"}
