from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from kai.content.faq import master_faq_system_block
from kai.content.loader import manifest_relative_path, read_text_file
from kai.settings import get_settings


def load_system_prompt_body() -> str:
    rel = manifest_relative_path("system_prompt", "system_prompt.md")
    return read_text_file(rel).strip()


def local_clock_block() -> str:
    from kai.workspace.runtime_settings import get_runtime_settings

    tz_name = (get_runtime_settings().timezone or get_settings().tz_region or "UTC").strip()
    now = datetime.now(ZoneInfo(tz_name))
    return (
        "## Current time (ground truth for scheduling)\n"
        f"- Now: `{now.strftime('%Y-%m-%d %H:%M')}` `{now.strftime('%A')}` — timezone `{tz_name}`\n"
        f"- Today's date for `visit_date`: `{now.strftime('%Y-%m-%d')}`\n"
        "- Interpret **today**, **tomorrow**, **tonight** from this section, not from training cutoff.\n"
    )


def build_system_prompt(tool_schemas: list[dict[str, Any]]) -> str:
    tool_block = "\n".join(
        f"- **{t['name']}**: {t['description']}"
        for t in tool_schemas
    )
    faq_block = master_faq_system_block()
    parts = [load_system_prompt_body(), local_clock_block()]
    if faq_block:
        parts.append(faq_block)
    parts.append(f"## Available tools\n{tool_block}\n")
    return "\n".join(parts)
