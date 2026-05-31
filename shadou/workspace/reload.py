from __future__ import annotations

"""Reload all workspace-backed caches (after admin refresh or hot edits)."""


def reload_workspace_caches() -> None:
    from shadou.content.channels import reload_channel_config
    from shadou.content.copy import reload_chat_copy
    from shadou.content.faq import invalidate_faq_cache
    from shadou.workspace.manifest import reload_workspace_manifest
    from shadou.workspace.runtime_settings import reload_workspace_settings_yaml
    from shadou.workspace.tools_config import reload_tools_config

    reload_workspace_manifest()
    reload_workspace_settings_yaml()
    reload_tools_config()
    reload_chat_copy()
    reload_channel_config()
    invalidate_faq_cache()
    from shadou.workspace.validate import invalidate_readiness_cache

    invalidate_readiness_cache()
    from config import reload_settings

    reload_settings()
