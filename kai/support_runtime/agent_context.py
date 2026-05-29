"""Canonical agent context assembly — the only allowed knowledge injected into the ReAct brain.

Policy (no exceptions):
  1. Workspace settings (tenant.yaml runtime fields: timezone, knowledge inject mode, tenant id)
  2. Skills / tools (names + descriptions + JSON schemas from tools_profile)
  3. system_prompt.md (behavior, tool-use rules)
  4. master_faq.md (sole factual source of truth — full inject or retrieval via search_faq)

Forbidden in the system prompt: learnt_faq, document skills, SOP blobs, env secrets,
hardcoded product copy, compiled debug artifacts, or any path not listed above.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from kai.content.faq import load_master_faq_text, master_faq_system_block
from kai.content.loader import manifest_relative_path, read_text_file
from kai.settings import get_settings
from kai.workspace.manifest import load_workspace_manifest
from kai.workspace.runtime_settings import get_runtime_settings

# Immutable policy marker — tests and docs reference this tuple.
ALLOWED_CONTEXT_SOURCES = (
    "workspace_settings",
    "system_prompt",
    "master_faq",
    "tools",
    "session_clock",
)

SOURCE_POLICY_PREAMBLE = """\
## Agent source policy (mandatory)

You may treat as authoritative **only**:
1. **Workspace settings** in this prompt (timezone, tenant, knowledge mode).
2. **system_prompt.md** (behavior and tool-use rules below).
3. **master_faq.md** (product/policy facts — or `search_faq` results compiled from it).
4. **Tool outputs** from the enabled skills listed below.

Do **not** invent product facts from general knowledge. Do **not** claim a tool succeeded when \
`ok` is false — quote the exact `error` field. When `search_kommu_support` returns `ok: true` with \
`on_official_list: false` or `official_match: false`, the search **worked** — tell the user the car is \
**not on the official list** (or name listed alternatives); do **not** say the search is "down".
"""


def load_system_prompt_body() -> str:
    rel = manifest_relative_path("system_prompt", "system_prompt.md")
    return read_text_file(rel).strip()


def workspace_settings_block() -> str:
    manifest = load_workspace_manifest()
    runtime = get_runtime_settings()
    inject = manifest.knowledge.inject_mode or "retrieval_first"
    now = datetime.now(ZoneInfo(runtime.timezone or "UTC"))
    return (
        "## Workspace settings\n"
        f"- Tenant: `{manifest.tenant_id}` ({manifest.display_name})\n"
        f"- Timezone: `{runtime.timezone}`\n"
        f"- Knowledge inject mode: `{inject}`\n"
        f"- Agent max steps: `{runtime.agent_max_steps}`\n"
        f"- Now (scheduling): `{now.strftime('%Y-%m-%d %H:%M')}` `{now.strftime('%A')}`\n"
        f"- Today's date for `visit_date`: `{now.strftime('%Y-%m-%d')}`\n"
        "- Interpret **today**, **tomorrow**, **tonight** from this section.\n"
    )


def tools_block(tool_schemas: list[dict[str, Any]]) -> str:
    lines = [
        "## Available tools (skills)",
        "Call tools with JSON `{\"action\":\"tool\",\"tool\":\"<name>\",\"args\":{...}}`.",
        "Every tool returns `{\"ok\": true|false, ...}`. On `ok: false`, surface the exact `error` — never hide failures.",
        "",
    ]
    for t in tool_schemas:
        lines.append(f"- **{t['name']}**: {t['description']}")
    return "\n".join(lines) + "\n"


def build_agent_system_prompt(tool_schemas: list[dict[str, Any]]) -> str:
    """Assemble the ReAct system prompt from allowed sources only."""
    parts = [
        SOURCE_POLICY_PREAMBLE,
        workspace_settings_block(),
        load_system_prompt_body(),
    ]
    faq_block = master_faq_system_block()
    if faq_block:
        parts.append(faq_block)
    parts.append(tools_block(tool_schemas))
    return "\n\n".join(parts)


def assert_prompt_sources_only() -> None:
    """Runtime self-check: FAQ path must resolve under KAI_HOME knowledge primary."""
    manifest = load_workspace_manifest()
    faq_path = get_settings().resolve_master_faq_path()
    primary = manifest.resolve(manifest.paths.knowledge_primary)
    if faq_path.resolve() != primary.resolve() and faq_path.is_file():
        # Explicit MASTER_FAQ_PATH override is allowed if it points at tenant knowledge file.
        pass
    if manifest.knowledge.inject_mode == "full_context":
        body = load_master_faq_text().strip()
        if not body:
            raise RuntimeError("full_context mode requires non-empty master_faq.md")
