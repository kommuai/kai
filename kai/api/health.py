from __future__ import annotations

from fastapi import APIRouter

import kai
from kai.engine.admin_token import admin_token_is_weak, require_strong_admin_token_enabled
from kai.settings import get_settings
from kai.support_runtime.compiler import _compiled_dir
from kai.workspace.manifest import load_workspace_manifest
from kai.workspace.tools_config import load_tools_config
from kai.workspace.validate import cached_readiness_issues, workspace_is_healthy

router = APIRouter(tags=["health"])


@router.get("/health")
def health_liveness():
    return {"status": "ok", "version": kai.__version__}


@router.get("/ready")
def health_readiness():
    settings = get_settings()
    manifest = load_workspace_manifest()
    tools = load_tools_config()
    chunks = _compiled_dir() / manifest.knowledge.compile_artifact
    issues = list(cached_readiness_issues())
    errors = [i for i in issues if i.level == "error"]

    llm_configured = bool((settings.kai_llm_api_key or settings.deepseek_api_key or "").strip())
    admin_weak = admin_token_is_weak()
    ready = workspace_is_healthy(issues) and chunks.is_file()
    if require_strong_admin_token_enabled() and admin_weak:
        ready = False

    from kai.engine.metrics import snapshot as metrics_snapshot

    payload = {
        "status": "ready" if ready else "degraded",
        "version": kai.__version__,
        "metrics": metrics_snapshot(),
        "tenant_id": manifest.tenant_id,
        "display_name": manifest.display_name,
        "workspace": str(settings.kai_home),
        "knowledge_chunks": chunks.is_file(),
        "tools_enabled": len(tools.enabled_entries()),
        "llm_configured": llm_configured,
        "admin_token_weak": admin_weak,
        "errors": [{"code": i.code, "message": i.message} for i in errors],
    }
    return payload
