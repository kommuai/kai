"""Run shadou.cli compile for a tenant workspace (SHADOU_HOME)."""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from shadou_paths import shadou_repo_root
from schemas import CompileResult


def run_tenant_compile(workspace_home: str | Path) -> CompileResult:
    home = str(Path(workspace_home).resolve())
    try:
        result = subprocess.run(
            ["python3", "-m", "shadou.cli", "compile"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(shadou_repo_root()),
            env={**os.environ, "SHADOU_HOME": home, "PYTHONPATH": str(shadou_repo_root())},
        )
        if result.returncode != 0:
            return CompileResult(ok=False, message=result.stderr or result.stdout or "compile failed")
        m = re.search(r"intents=(\d+)", result.stdout)
        intents = int(m.group(1)) if m else None
        return CompileResult(ok=True, message=(result.stdout or "").strip(), intents=intents)
    except subprocess.TimeoutExpired:
        return CompileResult(ok=False, message="Compile timed out")
    except Exception as exc:  # noqa: BLE001
        return CompileResult(ok=False, message=str(exc))


def patch_list_touches_faq(applied: list[dict[str, str]]) -> bool:
    return any(
        (row.get("file") or "").strip() == "faq"
        or (row.get("type") or "").strip() == "faq_intent"
        for row in applied
    )
