from __future__ import annotations

import logging
import os
from pathlib import Path

from shadou.settings import get_settings
from shadou.workspace.tools_config import enabled_canonical_builtins, needs_warranty_cache


def should_compile_at_startup() -> bool:
    raw = os.getenv("SHADOU_STARTUP_COMPILE", "1").strip().lower()
    if raw in {"0", "false", "no", "off"}:
        return False
    if raw in {"auto", "if_missing"}:
        from shadou.workspace.manifest import load_workspace_manifest

        manifest = load_workspace_manifest()
        chunks = (
            get_settings().shadou_home
            / manifest.paths.knowledge_compiled_dir
            / manifest.knowledge.compile_artifact
        )
        return not chunks.is_file()
    return True


def run_startup(*, compile_kb: bool | None = None) -> dict:
    """Validate workspace, warm caches needed for enabled tools only."""
    from shadou.core.workspace_manifest import log_session_store_hint
    from shadou.services.container import get_support_runtime_service
    from shadou.workspace.manifest import load_workspace_manifest
    from shadou.workspace.validate import validate_workspace, workspace_is_healthy

    log = logging.getLogger("shadou.startup")
    manifest = load_workspace_manifest()
    ws = get_settings().shadou_home
    log.info("tenant=%s workspace=%s", manifest.tenant_id, ws)

    do_compile = should_compile_at_startup() if compile_kb is None else compile_kb
    # Structure checks only; FAQ compile runs once in SupportRuntimeService.startup.
    issues = validate_workspace(compile_kb=False, ping_llm=False)
    for issue in issues:
        log.log(
            logging.ERROR if issue.level == "error" else logging.WARNING if issue.level == "warn" else logging.INFO,
            "%s %s: %s",
            issue.level,
            issue.code,
            issue.message,
        )

    strict = os.getenv("SHADOU_STRICT_STARTUP", "").strip().lower() in {"1", "true", "yes", "on"}
    if strict and not workspace_is_healthy(issues):
        raise RuntimeError("Workspace validation failed (SHADOU_STRICT_STARTUP=1)")

    from shadou.engine.admin_token import assert_admin_token_acceptable_for_boot

    assert_admin_token_acceptable_for_boot()
    if strict:
        from shadou.services.container import get_shadou_service

        get_shadou_service()

    log_session_store_hint()
    warm_warranty = needs_warranty_cache()
    counts = get_support_runtime_service().startup(
        compile_kb=do_compile,
        warm_warranty=warm_warranty,
    )
    return {"tenant_id": manifest.tenant_id, "compile_kb": do_compile, "warm_warranty": warm_warranty, **counts}
