from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable

from kai.support_runtime.retrieval import HybridRetriever, SimpleReranker
from kai.support_runtime.tools.catalog import builtin_catalog, resolve_builtin_id
from kai.support_runtime.tools.handlers import ToolHandlers
from kai.tools_plugins.runner import run_plugin_tool


@dataclass
class ToolDef:
    name: str
    description: str
    schema: dict[str, Any]
    handler: Callable[..., dict[str, Any]]


class AgentToolRegistry:
    def __init__(self, retriever: HybridRetriever, reranker: SimpleReranker) -> None:
        self.retriever = retriever
        self.reranker = reranker
        self._tools: dict[str, ToolDef] = {}
        self._tool_params: dict[str, dict[str, Any]] = {}
        self._context_user_id: str = ""
        self._handlers = ToolHandlers(self, retriever, reranker)
        self._register_from_workspace()

    def set_context(self, *, user_id: str = "") -> None:
        self._context_user_id = (user_id or "").strip()

    def list_schemas(self) -> list[dict[str, Any]]:
        return [{"name": t.name, "description": t.description, "schema": t.schema} for t in self._tools.values()]

    def call(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        tool = self._tools.get(name)
        if not tool:
            return {"ok": False, "error": f"unknown_tool:{name}"}
        try:
            return tool.handler(**(args or {}))
        except TypeError as exc:
            return {"ok": False, "error": f"invalid_args:{exc}"}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": f"tool_failed:{exc}"}

    def _register(self, tool: ToolDef) -> None:
        self._tools[tool.name] = tool

    def __getattr__(self, name: str) -> Any:
        """Delegate handler access for tests and legacy call sites."""
        try:
            return getattr(self._handlers, name)
        except AttributeError as exc:
            raise AttributeError(name) from exc

    def _register_from_workspace(self) -> None:
        from kai.workspace.tools_config import load_tools_config

        catalog = builtin_catalog()
        for entry in load_tools_config().enabled_entries():
            self._tool_params[entry.id] = dict(entry.params or {})

            if entry.plugin:
                plugin_id = entry.plugin

                def _plugin_handler(_pid=plugin_id, _params=entry.params, **kwargs: Any) -> dict[str, Any]:
                    return run_plugin_tool(_pid, _params, kwargs)

                schema = entry.params.get("schema") if isinstance(entry.params.get("schema"), dict) else {
                    "type": "object",
                    "properties": {
                        "visit_date": {"type": "string"},
                        "visit_time": {"type": "string"},
                        "unit_id": {"type": "string"},
                    },
                }
                self._register(
                    ToolDef(
                        name=entry.id,
                        description=entry.description or f"Plugin: {plugin_id}",
                        schema=schema,
                        handler=_plugin_handler,
                    )
                )
                continue

            canonical = resolve_builtin_id(entry.builtin)
            spec = catalog.get(canonical)
            if not spec:
                continue
            handler = getattr(self._handlers, spec.handler_name, None)
            if not callable(handler):
                continue
            self._register(
                ToolDef(
                    name=entry.id,
                    description=entry.description or spec.description,
                    schema=spec.schema,
                    handler=handler,
                )
            )


def parse_tool_call(raw: str) -> tuple[str, dict[str, Any]] | tuple[None, None]:
    text = (raw or "").strip()
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        return None, None
    try:
        obj = json.loads(m.group(0))
    except Exception:
        return None, None
    name = str(obj.get("tool", "")).strip()
    args = obj.get("args") or {}
    if not isinstance(args, dict):
        args = {}
    if not name:
        return None, None
    return name, args
