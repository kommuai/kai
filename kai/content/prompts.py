"""Backward-compatible prompt helpers — assembly lives in agent_context."""

from __future__ import annotations

from typing import Any

from kai.support_runtime.agent_context import (
    build_agent_system_prompt,
    load_system_prompt_body,
    workspace_settings_block,
)

# Legacy name used by tests and callers.
local_clock_block = workspace_settings_block


def build_system_prompt(tool_schemas: list[dict[str, Any]]) -> str:
    return build_agent_system_prompt(tool_schemas)
