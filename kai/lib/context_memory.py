"""Deprecated: session context is full chat history + master_faq in system prompt."""

from __future__ import annotations


def build_turn_memory_block(user_id: str, *, extra: str = "") -> str:
    """No longer injects regex topic stickiness or FAQ hints. Returns empty."""
    return ""
