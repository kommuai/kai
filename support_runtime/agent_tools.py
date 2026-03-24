from __future__ import annotations

from dataclasses import dataclass
import json
from functools import lru_cache
import html
import re
from typing import Any, Callable

import requests

from config import BING_API_KEY, VEHICLE_SUPPORT_HTTP_TIMEOUT_SECONDS, VEHICLE_SUPPORT_OFFICIAL_URL
from google_sheets import warranty_lookup_by_dongle, warranty_text_from_row
from support_runtime.retrieval import HybridRetriever, SimpleReranker
from support_runtime.tech_backlog import (
    append_backlog_issue,
    bukapilot_agentic_search,
    find_similar_active_issue,
    infer_possible_solution_from_bukapilot,
)


def _strip_html(raw: str) -> str:
    txt = html.unescape(raw or "")
    txt = re.sub(r"(?is)<script.*?>.*?</script>", " ", txt)
    txt = re.sub(r"(?is)<style.*?>.*?</style>", " ", txt)
    txt = re.sub(r"(?s)<[^>]+>", " ", txt)
    return re.sub(r"\s+", " ", txt).strip()


@lru_cache(maxsize=1)
def _kommu_support_text() -> str:
    try:
        resp = requests.get(VEHICLE_SUPPORT_OFFICIAL_URL, timeout=VEHICLE_SUPPORT_HTTP_TIMEOUT_SECONDS)
        if not resp.ok:
            return ""
        return _strip_html(resp.text)
    except Exception:
        return ""


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
        self._register_defaults()

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

    def _register_defaults(self) -> None:
        self._register(
            ToolDef(
                name="search_faq",
                description="Semantic FAQ lookup over compiled knowledge chunks",
                schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
                handler=self.search_faq,
            )
        )
        self._register(
            ToolDef(
                name="search_web",
                description="General web search via Bing",
                schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
                handler=self.search_web,
            )
        )
        self._register(
            ToolDef(
                name="search_kommu_support",
                description="Search official kommu.ai/support content",
                schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
                handler=self.search_kommu_support,
            )
        )
        self._register(
            ToolDef(
                name="search_bukapilot",
                description="Search bukapilot repo for possible fixes",
                schema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}, "branch": {"type": "string"}},
                    "required": ["query"],
                },
                handler=self.search_bukapilot,
            )
        )
        self._register(
            ToolDef(
                name="lookup_warranty",
                description="Lookup warranty by dongle id",
                schema={"type": "object", "properties": {"dongle_id": {"type": "string"}}, "required": ["dongle_id"]},
                handler=self.lookup_warranty,
            )
        )
        self._register(
            ToolDef(
                name="lookup_backlog",
                description="Find similar active issue in backlog Active tab",
                schema={"type": "object", "properties": {"issue_summary": {"type": "string"}}, "required": ["issue_summary"]},
                handler=self.lookup_backlog,
            )
        )
        self._register(
            ToolDef(
                name="log_backlog",
                description="Append unresolved issue to Chatbot Backlog",
                schema={
                    "type": "object",
                    "properties": {"issue": {"type": "string"}, "possible_solution": {"type": "string"}},
                    "required": ["issue"],
                },
                handler=self.log_backlog,
            )
        )
        self._register(
            ToolDef(
                name="escalate_to_human",
                description="Mark case for human escalation",
                schema={"type": "object", "properties": {"reason": {"type": "string"}}, "required": ["reason"]},
                handler=self.escalate_to_human,
            )
        )

    def search_faq(self, query: str) -> dict[str, Any]:
        items = self.retriever.retrieve(query, top_k=8)
        ranked = self.reranker.rerank(query, items, top_k=4)
        return {
            "ok": True,
            "results": [{"source_id": r.source_id, "text": r.text, "score": r.score, "metadata": r.metadata} for r in ranked],
        }

    def search_web(self, query: str) -> dict[str, Any]:
        if not BING_API_KEY:
            return {"ok": False, "error": "missing_bing_api_key", "results": []}
        try:
            resp = requests.get(
                "https://api.bing.microsoft.com/v7.0/search",
                params={"q": query, "count": 5, "textFormat": "Raw"},
                headers={"Ocp-Apim-Subscription-Key": BING_API_KEY},
                timeout=VEHICLE_SUPPORT_HTTP_TIMEOUT_SECONDS,
            )
            if not resp.ok:
                return {"ok": False, "error": f"bing_http_{resp.status_code}", "results": []}
            items = ((resp.json() or {}).get("webPages") or {}).get("value") or []
            out = [{"url": i.get("url", ""), "name": i.get("name", ""), "snippet": i.get("snippet", "")} for i in items[:5]]
            return {"ok": True, "results": out}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": f"bing_exception:{exc}", "results": []}

    def search_kommu_support(self, query: str) -> dict[str, Any]:
        corpus = _kommu_support_text()
        if not corpus:
            return {"ok": False, "error": "official_support_unavailable", "results": []}
        terms = [t for t in re.split(r"[^a-z0-9]+", query.lower()) if t]
        sentences = re.split(r"(?<=[\.\!\?])\s+", corpus)
        scored: list[tuple[float, str]] = []
        for s in sentences:
            t = s.lower()
            overlap = sum(1 for tok in terms if tok in t)
            if overlap:
                scored.append((overlap / max(1, len(terms)), s.strip()))
        scored.sort(key=lambda x: x[0], reverse=True)
        return {
            "ok": True,
            "source_url": VEHICLE_SUPPORT_OFFICIAL_URL,
            "results": [{"text": s, "score": sc} for sc, s in scored[:5]],
        }

    def search_bukapilot(self, query: str, branch: str = "") -> dict[str, Any]:
        return bukapilot_agentic_search(query, branch=branch or None, max_hits=5)

    def lookup_warranty(self, dongle_id: str) -> dict[str, Any]:
        row = warranty_lookup_by_dongle((dongle_id or "").strip())
        if not row:
            return {"ok": False, "found": False}
        return {"ok": True, "found": True, "answer": warranty_text_from_row(row), "row": row}

    def lookup_backlog(self, issue_summary: str) -> dict[str, Any]:
        return find_similar_active_issue(issue_summary)

    def log_backlog(self, issue: str, possible_solution: str = "") -> dict[str, Any]:
        solution = possible_solution.strip() if possible_solution else infer_possible_solution_from_bukapilot(issue)
        return append_backlog_issue(issue, solution)

    def escalate_to_human(self, reason: str) -> dict[str, Any]:
        return {"ok": True, "escalate": True, "reason": reason}


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
