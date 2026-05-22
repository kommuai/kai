"""Backward-compatible import path — implementation lives in kai.support_runtime.tools."""

from kai.support_runtime.tools.registry import AgentToolRegistry, ToolDef, parse_tool_call

__all__ = ["AgentToolRegistry", "ToolDef", "parse_tool_call"]
