from __future__ import annotations

import logging
import os
from pathlib import Path

from kai.settings import get_settings
from kai.workspace.tools_config import enabled_canonical_builtins, needs_warranty_cache


def should_compile_at_startup() -> bool:
    raw = os.getenv("KAI_STARTUP_COMPILE", "1").strip().lower()
    if raw in {"0", "false", "no", "off"}:
        return False
    if raw in {"auto", "if_missing"}:
        from kai.workspace.manifest import load_workspace_manifest

        manifest = load_workspace_manifest()
        chunks = (
            get_settings().kai_home
            / manifest.paths.knowledge_compiled_dir
            / manifest.knowledge.compile_artifact
        )
        return not chunks.is_file()
    return True


def run_startup(*, compile_kb: bool | None = None) -> dict:
    """Validate workspace, warm caches needed for enabled tools only."""
    from kai.core.workspace_manifest import log_session_store_hint
    from kai.services.container import get_support_runtime_service
    from kai.workspace.manifest import load_workspace_manifest
    from kai.workspace.validate import validate_workspace, workspace_is_healthy

    log = logging.getLogger("kai.startup")
    manifest = load_workspace_manifest()
    ws = get_settings().kai_home
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

    strict = os.getenv("KAI_STRICT_STARTUP", "").strip().lower() in {"1", "true", "yes", "on"}
    if strict and not workspace_is_healthy(issues):
        raise RuntimeError("Workspace validation failed (KAI_STRICT_STARTUP=1)")

    from kai.engine.admin_token import assert_admin_token_acceptable_for_boot

    assert_admin_token_acceptable_for_boot()
    if strict:
        from kai.services.container import get_kai_service

        get_kai_service()

    log_session_store_hint()
    warm_warranty = needs_warranty_cache()
    counts = get_support_runtime_service().startup(
        compile_kb=do_compile,
        warm_warranty=warm_warranty,
    )
    return {"tenant_id": manifest.tenant_id, "compile_kb": do_compile, "warm_warranty": warm_warranty, **counts}
