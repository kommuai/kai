from __future__ import annotations

"""Reload all workspace-backed caches (after admin refresh or hot edits)."""


def reload_workspace_caches() -> None:
    from kai.content.channels import reload_channel_config
    from kai.content.copy import reload_chat_copy
    from kai.content.faq import invalidate_faq_cache
    from kai.workspace.manifest import reload_workspace_manifest
    from kai.workspace.runtime_settings import reload_workspace_settings_yaml
    from kai.workspace.tools_config import reload_tools_config

    reload_workspace_manifest()
    reload_workspace_settings_yaml()
    reload_tools_config()
    reload_chat_copy()
    reload_channel_config()
    invalidate_faq_cache()
    from kai.workspace.validate import invalidate_readiness_cache

    invalidate_readiness_cache()
    from config import reload_settings

    reload_settings()
