from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from typing import Any

import requests

from kai.support_runtime.canonical_faq import extract_answer_from_chunk, pick_best_canonical
from kai.support_runtime.retrieval import HybridRetriever, SimpleReranker
from kai.support_runtime.tools.catalog import resolve_builtin_id
from kai.support_runtime.tools.site_search import match_vehicle_catalog, support_site_corpus


class ToolHandlers:
    """Built-in tool implementations; kept free of tenant brand strings."""

    def __init__(self, registry: Any, retriever: HybridRetriever, reranker: SimpleReranker) -> None:
        self._registry = registry
        self.retriever = retriever
        self.reranker = reranker

    def _params(self, canonical_id: str) -> dict[str, Any]:
        """Params for a canonical builtin; falls back to any enabled tool id that aliases to it."""
        store = getattr(self._registry, "_tool_params", {})
        direct = dict(store.get(canonical_id) or {})
        if direct:
            return direct
        for tid, params in store.items():
            if resolve_builtin_id(tid) == canonical_id:
                return dict(params or {})
        return {}

    def _http_timeout(self) -> int:
        try:
            from kai.settings import get_settings

            return int(get_settings().vehicle_support_http_timeout_seconds)
        except Exception:  # noqa: BLE001
            return 8

    def search_session_memory(self, query: str, limit: int = 5) -> dict[str, Any]:
        from kai.lib.session_search import search_user_messages

        uid = getattr(self._registry, "_context_user_id", "")
        return search_user_messages(uid, query, limit=int(limit or 5))

    def search_faq(self, query: str) -> dict[str, Any]:
        items = self.retriever.retrieve(query, top_k=8)
        ranked = self.reranker.rerank(query, items, top_k=4)
        rows: list[dict[str, Any]] = []
        for r in ranked:
            canonical = extract_answer_from_chunk(r.text)
            rows.append({
                "source_id": r.source_id,
                "text": r.text,
                "canonical_answer": canonical,
                "score": r.score,
                "metadata": r.metadata,
            })
        payload: dict[str, Any] = {"ok": True, "results": rows}
        best = pick_best_canonical({"results": rows})
        if best:
            payload["best_canonical"] = best
        return payload

    def search_web(self, query: str) -> dict[str, Any]:
        from kai.settings import get_settings

        key = (get_settings().bing_api_key or "").strip()
        if not key:
            return {"ok": False, "error": "missing_bing_api_key", "results": []}
        try:
            resp = requests.get(
                "https://api.bing.microsoft.com/v7.0/search",
                params={"q": query, "count": 5, "textFormat": "Raw"},
                headers={"Ocp-Apim-Subscription-Key": key},
                timeout=self._http_timeout(),
            )
            if not resp.ok:
                return {"ok": False, "error": f"bing_http_{resp.status_code}", "results": []}
            items = ((resp.json() or {}).get("webPages") or {}).get("value") or []
            out = [
                {"url": i.get("url", ""), "name": i.get("name", ""), "snippet": i.get("snippet", "")}
                for i in items[:5]
            ]
            return {"ok": True, "results": out}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": f"bing_exception:{exc}", "results": []}

    def search_official_site(self, query: str) -> dict[str, Any]:
        p = self._params("search_official_site")
        official_url = str(p.get("official_url") or "").strip()
        vehicles_url = str(p.get("vehicles_json_url") or p.get("vehicles_url") or "").strip()

        from kai.support_runtime.tools.site_search import (
            catalog_list_result,
            catalog_miss_detail,
            format_catalog_miss_text,
            is_catalog_list_query,
        )

        if is_catalog_list_query(query):
            listed = catalog_list_result(vehicles_json_url=vehicles_url, timeout=self._http_timeout())
            if listed:
                listed["source_url"] = official_url
                return listed

        matched = match_vehicle_catalog(query, vehicles_json_url=vehicles_url, timeout=self._http_timeout())
        if matched:
            years = sorted(matched.get("years") or [])
            year_text = f"{years[0]}-{years[-1]}" if years else "listed"
            variant = str(matched.get("variant") or "").strip()
            text = f"{matched.get('name')} {year_text}".strip()
            if variant:
                text += f" ({variant})"
            return {
                "ok": True,
                "source_url": official_url,
                "results": [{"text": text, "score": 1.0, "official_match": True}],
            }

        miss = catalog_miss_detail(query, vehicles_json_url=vehicles_url, timeout=self._http_timeout())
        if miss:
            return {
                "ok": True,
                "source_url": official_url,
                "official_match": False,
                "on_official_list": False,
                "catalog_checked": True,
                "results": [{"text": format_catalog_miss_text(miss), "score": 1.0, "official_match": False}],
            }

        corpus = support_site_corpus(official_url, timeout=self._http_timeout())
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
            "source_url": official_url,
            "results": [{"text": s, "score": sc} for sc, s in scored[:5]],
        }

    def search_github_repo(self, query: str, branch: str = "") -> dict[str, Any]:
        from kai.support_runtime.tech_backlog import github_repo_agentic_search

        p = self._params("search_github_repo")
        repo = str(p.get("repo") or os.getenv("KAI_GITHUB_REPO", "")).strip().strip("/")
        br = (branch or str(p.get("branch") or os.getenv("KAI_GITHUB_BRANCH", ""))).strip()
        return github_repo_agentic_search(query, branch=br or None, max_hits=5, repo=repo or None)

    def read_github_file(self, path: str, branch: str = "") -> dict[str, Any]:
        p = self._params("read_github_file")
        repo = str(p.get("repo") or os.getenv("KAI_GITHUB_REPO", "")).strip().strip("/")
        br = (branch or str(p.get("branch") or os.getenv("KAI_GITHUB_BRANCH", "main"))).strip() or "main"
        rel = (path or "").strip().lstrip("/")
        if not rel:
            return {"ok": False, "error": "missing_path", "content": ""}
        if not repo:
            return {"ok": False, "error": "missing_github_repo", "content": ""}
        url = f"https://raw.githubusercontent.com/{repo}/{br}/{rel}"
        headers: dict[str, str] = {}
        token = (os.getenv("KAI_GITHUB_TOKEN") or "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            resp = requests.get(url, headers=headers, timeout=self._http_timeout())
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": f"fetch_failed:{exc}", "content": ""}
        if not resp.ok:
            return {
                "ok": False,
                "error": f"http_{resp.status_code}",
                "url": url,
                "content": (resp.text or "")[:2000],
            }
        text = resp.text or ""
        max_chars = int(p.get("max_chars") or 80_000)
        truncated = len(text) > max_chars
        if truncated:
            text = text[:max_chars]
        return {
            "ok": True,
            "path": rel,
            "branch": br,
            "truncated": truncated,
            "char_count": len(text),
            "content": text,
        }

    def lookup_sheet_record(self, record_id: str = "", dongle_id: str = "") -> dict[str, Any]:
        from kai.lib.google_sheets import warranty_lookup_by_dongle, warranty_text_from_row

        rid = (record_id or dongle_id or "").strip()
        if not rid:
            return {"ok": False, "error": "missing_record_id", "found": False}
        row = warranty_lookup_by_dongle(rid)
        if not row:
            return {"ok": False, "found": False}
        return {"ok": True, "found": True, "answer": warranty_text_from_row(row), "row": row}

    def lookup_sheet_backlog(self, issue_summary: str) -> dict[str, Any]:
        from kai.support_runtime.tech_backlog import find_similar_active_issue

        return find_similar_active_issue(issue_summary)

    def log_sheet_backlog(
        self,
        issue: str,
        device: str = "Unknown",
        car: str = "Unknown",
        **_ignored: Any,
    ) -> dict[str, Any]:
        from kai.lib.deepseek_client import chat_completion as deepseek_chat_completion
        from kai.support_runtime.tech_backlog import append_backlog_issue, summarize_issue

        p = self._params("log_sheet_backlog") or self._params("log_backlog")
        dev = (device or "").strip()
        car_s = (car or "").strip()
        if not dev or dev.lower() == "unknown" or not car_s or car_s.lower() == "unknown":
            return {"ok": False, "error": "log_backlog_not_ready_missing_device_car"}

        system_prompt = str(
            p.get("summarize_system_prompt")
            or (
                "You are a technical support writer. Given a customer issue report, produce a concise note. "
                'Return ONLY JSON with keys "problem_description" and "reproduction_steps".'
            )
        )
        user_prompt = (
            f"Device: {dev}\nCar: {car_s}\n\nIssue report:\n{issue}\n\nReturn only JSON."
        )
        raw = deepseek_chat_completion(system_prompt, user_prompt)
        parsed = _extract_json_object(raw or "")
        problem_description = str(parsed.get("problem_description") or "").strip()
        reproduction_steps = str(parsed.get("reproduction_steps") or "").strip()
        if not problem_description:
            problem_description = summarize_issue(issue, product_class="", device="", car="", category="")
        return append_backlog_issue(
            device=dev,
            car=car_s,
            issue_description=problem_description[:2000],
            reproduction_steps=reproduction_steps[:2000] if reproduction_steps else "",
        )

    def escalate_to_human(self, reason: str) -> dict[str, Any]:
        return {"ok": True, "escalate": True, "reason": reason}


def _extract_json_object(text: str) -> dict[str, Any]:
    m = re.search(r"\{.*\}", text or "", flags=re.S)
    if not m:
        return {}
    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}
