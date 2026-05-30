from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from kai.workspace.manifest import load_workspace_data

CORE_TOOL_IDS: tuple[str, ...] = (
    "search_faq",
    "search_session_memory",
    "escalate_to_human",
)

# Reference profiles for tools.yaml (tenant packs may override)
TOOL_PROFILES: dict[str, tuple[str, ...]] = {
    "minimal": ("search_faq", "search_session_memory", "escalate_to_human"),
    "standard": CORE_TOOL_IDS + ("search_official_site", "lookup_sheet_record"),
}


@dataclass(frozen=True)
class BuiltinToolSpec:
    builtin_id: str
    handler_name: str
    description: str
    schema: dict[str, Any]


@lru_cache(maxsize=1)
def load_tool_aliases() -> dict[str, str]:
    """Tenant-defined legacy tool id → canonical builtin handler id."""
    data = load_workspace_data()
    tp = data.get("tools_profile") if isinstance(data.get("tools_profile"), dict) else {}
    raw = tp.get("tool_aliases")
    if not isinstance(raw, dict):
        return {}
    return {str(k).strip(): str(v).strip() for k, v in raw.items() if str(k).strip() and str(v).strip()}


def reload_tool_aliases() -> dict[str, str]:
    load_tool_aliases.cache_clear()
    load_workspace_data.cache_clear()
    return load_tool_aliases()


def resolve_builtin_id(builtin: str) -> str:
    bid = (builtin or "").strip()
    if not bid:
        return bid
    return load_tool_aliases().get(bid, bid)


def _schema_object(*, props: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {"type": "object", "properties": props, "required": required or []}


def builtin_catalog() -> dict[str, BuiltinToolSpec]:
    return {
        "search_faq": BuiltinToolSpec(
            builtin_id="search_faq",
            handler_name="search_faq",
            description="Semantic FAQ lookup over compiled knowledge chunks",
            schema=_schema_object(props={"query": {"type": "string"}}, required=["query"]),
        ),
        "search_session_memory": BuiltinToolSpec(
            builtin_id="search_session_memory",
            handler_name="search_session_memory",
            description="Search this user's earlier messages in the current session (FTS).",
            schema=_schema_object(
                props={
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "description": "Max hits (default 5)"},
                },
                required=["query"],
            ),
        ),
        "search_official_site": BuiltinToolSpec(
            builtin_id="search_official_site",
            handler_name="search_official_site",
            description="Search official support site content (params: official_url, vehicles_json_url)",
            schema=_schema_object(props={"query": {"type": "string"}}, required=["query"]),
        ),
        "search_github_repo": BuiltinToolSpec(
            builtin_id="search_github_repo",
            handler_name="search_github_repo",
            description="Search a GitHub repo for fixes (params: repo, branch)",
            schema=_schema_object(
                props={"query": {"type": "string"}, "branch": {"type": "string"}},
                required=["query"],
            ),
        ),
        "read_github_file": BuiltinToolSpec(
            builtin_id="read_github_file",
            handler_name="read_github_file",
            description="Read a file from a GitHub repo (params: repo, branch)",
            schema=_schema_object(
                props={
                    "path": {"type": "string", "description": "Repo-relative path"},
                    "branch": {"type": "string"},
                },
                required=["path"],
            ),
        ),
        "lookup_sheet_record": BuiltinToolSpec(
            builtin_id="lookup_sheet_record",
            handler_name="lookup_sheet_record",
            description="Lookup a record in a configured sheet/CSV index (params: id_field, default dongle_id)",
            schema=_schema_object(
                props={"record_id": {"type": "string"}, "dongle_id": {"type": "string"}},
                required=[],
            ),
        ),
        "lookup_sheet_backlog": BuiltinToolSpec(
            builtin_id="lookup_sheet_backlog",
            handler_name="lookup_sheet_backlog",
            description="Find similar open issue in configured backlog sheet",
            schema=_schema_object(props={"issue_summary": {"type": "string"}}, required=["issue_summary"]),
        ),
        "log_sheet_backlog": BuiltinToolSpec(
            builtin_id="log_sheet_backlog",
            handler_name="log_sheet_backlog",
            description="Append issue to configured backlog sheet (requires device + car in args)",
            schema=_schema_object(
                props={
                    "issue": {"type": "string"},
                    "device": {"type": "string"},
                    "car": {"type": "string"},
                },
                required=["issue"],
            ),
        ),
        "escalate_to_human": BuiltinToolSpec(
            builtin_id="escalate_to_human",
            handler_name="escalate_to_human",
            description="Mark case for human escalation",
            schema=_schema_object(props={"reason": {"type": "string"}}, required=["reason"]),
        ),
    }


def default_tool_ids() -> list[str]:
    return list(CORE_TOOL_IDS)
