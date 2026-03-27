from __future__ import annotations

from dataclasses import dataclass
import json
from functools import lru_cache
import html
import os
from pathlib import Path
import re
import subprocess
from typing import Any, Callable

import requests

from config import (
    BING_API_KEY,
    BUKAPILOT_BRANCH,
    BUKAPILOT_REPO,
    VEHICLE_SUPPORT_HTTP_TIMEOUT_SECONDS,
    VEHICLE_SUPPORT_OFFICIAL_URL,
)
from google_sheets import warranty_lookup_by_dongle, warranty_text_from_row
from support_runtime.retrieval import HybridRetriever, SimpleReranker
from support_runtime.tech_backlog import (
    append_backlog_issue,
    bukapilot_agentic_search,
    find_similar_active_issue,
    infer_possible_solution_from_bukapilot,
    summarize_issue,
)
from deepseek_client import chat_completion as deepseek_chat_completion


def _strip_html(raw: str) -> str:
    txt = html.unescape(raw or "")
    txt = re.sub(r"(?is)<script.*?>.*?</script>", " ", txt)
    txt = re.sub(r"(?is)<style.*?>.*?</style>", " ", txt)
    txt = re.sub(r"(?s)<[^>]+>", " ", txt)
    return re.sub(r"\s+", " ", txt).strip()


def _expand_years(raw: str) -> set[int]:
    text = str(raw or "")
    years: set[int] = set()
    for a, b in re.findall(r"((?:19|20)\d{2})\s*[–-]\s*((?:19|20)\d{2})", text):
        years.update(range(int(a), int(b) + 1))
    for y in re.findall(r"\b((?:19|20)\d{2})\b", text):
        years.add(int(y))
    return {y for y in years if 1980 <= y <= 2035}


@lru_cache(maxsize=1)
def _kommu_support_text() -> str:
    try:
        resp = requests.get(VEHICLE_SUPPORT_OFFICIAL_URL, timeout=VEHICLE_SUPPORT_HTTP_TIMEOUT_SECONDS)
        if not resp.ok:
            return ""
        return _strip_html(resp.text)
    except Exception:
        return ""


@lru_cache(maxsize=1)
def _official_supported_vehicles() -> list[dict[str, Any]]:
    # Support page itself is JS-driven; it references this official data source.
    source = "https://raw.githubusercontent.com/kommuai/bukapilot/snapshot/selfdrive/car/supported_vehicle.json"
    try:
        resp = requests.get(source, timeout=VEHICLE_SUPPORT_HTTP_TIMEOUT_SECONDS)
        if not resp.ok:
            return []
        obj = resp.json()
    except Exception:
        return []

    rows: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    if isinstance(obj, dict):
        for v in obj.values():
            if isinstance(v, list):
                items.extend([x for x in v if isinstance(x, dict)])
    elif isinstance(obj, list):
        items = [x for x in obj if isinstance(x, dict)]

    for row in items:
        brand = str(row.get("brand") or "").strip()
        model = str(row.get("model") or "").strip()
        if not (brand or model):
            continue
        years = _expand_years(row.get("year") or "")
        variant = str(row.get("variant") or "").strip()
        rows.append(
            {
                "name": f"{brand} {model}".strip(),
                "brand": brand,
                "model": model,
                "years": years,
                "variant": variant,
            }
        )
    return rows


def _match_official_vehicle(query: str) -> dict[str, Any] | None:
    vehicles = _official_supported_vehicles()
    if not vehicles:
        return None
    q = (query or "").lower()
    if not q:
        return None
    year_m = re.search(r"\b(19|20)\d{2}\b", q)
    q_year = int(year_m.group(0)) if year_m else None
    stop = {"is", "my", "car", "support", "supported", "do", "you", "can", "vehicle", "kommu"}
    q_tokens = [t for t in re.split(r"[^a-z0-9]+", q) if len(t) >= 3 and t not in stop]
    if not q_tokens:
        return None

    best = None
    best_score = -1
    for row in vehicles:
        name_l = str(row.get("name") or "").lower()
        token_hits = sum(1 for t in q_tokens if t in name_l)
        if token_hits < 2:
            continue
        years = row.get("years") or set()
        if q_year is not None and years and q_year not in years:
            continue
        score = token_hits + (2 if q_year is not None and q_year in years else 0)
        if score > best_score:
            best_score = score
            best = row
    return best


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
                name="read_bukapilot_file",
                description=(
                    "Fetch and read a specific file from the bukapilot repo (e.g. RELEASES.md for changelogs). "
                    "Use after search_bukapilot when you need full file contents."
                ),
                schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Repo-relative path, e.g. RELEASES.md"},
                        "branch": {
                            "type": "string",
                            "description": f"Git branch (default {BUKAPILOT_BRANCH})",
                        },
                    },
                    "required": ["path"],
                },
                handler=self.read_bukapilot_file,
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
                description=(
                    "Append an issue to Chatbot Backlog (5 columns: timestamp, device, car, problem description, reproduction steps). "
                    "Before calling, determine from the conversation (or ask) device type (KA2/KA1/KA1s) and "
                    "car brand/model/year. Tool will refuse to log if `device` or `car` are `Unknown`."
                ),
                schema={
                    "type": "object",
                    "properties": {
                        "issue": {"type": "string", "description": "Detailed issue summary"},
                        "device": {
                            "type": "string",
                            "description": "KA2, KA1, KA1s, or Unknown",
                        },
                        "car": {
                            "type": "string",
                            "description": "Brand model year, or Unknown",
                        },
                    },
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
        self._register(
            ToolDef(
                name="create_visitor_pass",
                description=(
                    "Create SMARTSERVA building-entry visitor pass (delivery) and return pass link. "
                    "Use for user requests about QR/link/pass to enter building."
                ),
                schema={
                    "type": "object",
                    "properties": {
                        "visit_date": {
                            "type": "string",
                            "description": "Visit date in YYYY-MM-DD (Malaysia calendar day when user specifies a day)",
                        },
                        "visit_time": {
                            "type": "string",
                            "description": "Visit time in HH:MM 24-hour Malaysia local time",
                        },
                        "unit_id": {
                            "type": "string",
                            "description": "Optional SMARTSERVA unit id override",
                        },
                    },
                },
                handler=self.create_visitor_pass,
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
        matched = _match_official_vehicle(query)
        if matched:
            years = sorted(matched.get("years") or [])
            year_text = f"{years[0]}-{years[-1]}" if years else "listed"
            variant = str(matched.get("variant") or "").strip()
            text = f"{matched.get('name')} {year_text}".strip()
            if variant:
                text += f" ({variant})"
            return {
                "ok": True,
                "source_url": VEHICLE_SUPPORT_OFFICIAL_URL,
                "results": [{"text": text, "score": 1.0, "official_match": True}],
            }

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

    def read_bukapilot_file(self, path: str, branch: str = "") -> dict[str, Any]:
        br = (branch or BUKAPILOT_BRANCH).strip() or "release_ka2"
        rel = (path or "").strip().lstrip("/")
        if not rel:
            return {"ok": False, "error": "missing_path", "content": ""}
        repo = (BUKAPILOT_REPO or "").strip().strip("/")
        if not repo:
            return {"ok": False, "error": "missing_bukapilot_repo", "content": ""}
        url = f"https://raw.githubusercontent.com/{repo}/{br}/{rel}"
        headers: dict[str, str] = {}
        token = (os.getenv("KAI_GITHUB_TOKEN") or "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            resp = requests.get(url, headers=headers, timeout=VEHICLE_SUPPORT_HTTP_TIMEOUT_SECONDS)
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
        max_chars = 80_000
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

    def lookup_warranty(self, dongle_id: str) -> dict[str, Any]:
        row = warranty_lookup_by_dongle((dongle_id or "").strip())
        if not row:
            return {"ok": False, "found": False}
        return {"ok": True, "found": True, "answer": warranty_text_from_row(row), "row": row}

    def lookup_backlog(self, issue_summary: str) -> dict[str, Any]:
        return find_similar_active_issue(issue_summary)

    def log_backlog(
        self,
        issue: str,
        device: str = "Unknown",
        car: str = "Unknown",
        **_ignored: Any,
    ) -> dict[str, Any]:
        dev = (device or "").strip()
        car_s = (car or "").strip()
        if not dev or dev.lower() == "unknown" or not car_s or car_s.lower() == "unknown":
            return {"ok": False, "error": "log_backlog_not_ready_missing_device_car"}
        def _extract_first_json_object(text: str) -> dict[str, Any]:
            # DeepSeek sometimes wraps JSON in extra text/markdown; extract the first {...} object.
            m = re.search(r"\{.*\}", text or "", flags=re.S)
            if not m:
                return {}
            try:
                obj = json.loads(m.group(0))
                return obj if isinstance(obj, dict) else {}
            except Exception:
                return {}

        system_prompt = (
            "You are a technical documentation writer for KommuAssist (KA2). "
            "Given a customer issue report, produce a concise technical note. "
            "Return ONLY a valid JSON object (no markdown, no code fences) with keys: "
            "\"problem_description\" and \"reproduction_steps\"."
        )
        user_prompt = (
            f"Device: {dev}\nCar: {car_s}\n\n"
            f"Issue report:\n{issue}\n\n"
            "problem_description: 1-3 sentences describing the problem in technical terms, "
            "including likely symptom, error codes mentioned, and relevant context from the report.\n"
            "reproduction_steps: a single paragraph describing how to reproduce the issue step-by-step "
            "in plain sentences (no bullet lists). If reproduction is unknown, write what the customer did "
            "and what conditions seem important.\n"
            "Return only JSON."
        )

        deepseek_raw = deepseek_chat_completion(system_prompt, user_prompt)
        parsed = _extract_first_json_object(deepseek_raw or "")

        problem_description = str(parsed.get("problem_description") or "").strip()
        reproduction_steps = str(parsed.get("reproduction_steps") or "").strip()

        if not problem_description:
            # Fallback: old heuristic summary.
            problem_description = summarize_issue(issue, product_class="", device="", car="", category="")
            reproduction_steps = ""

        # Keep sheet cells reasonably bounded.
        problem_description = problem_description[:2000]
        reproduction_steps = reproduction_steps[:2000] if reproduction_steps else ""

        return append_backlog_issue(
            device=dev,
            car=car_s,
            issue_description=problem_description,
            reproduction_steps=reproduction_steps,
        )

    def escalate_to_human(self, reason: str) -> dict[str, Any]:
        return {"ok": True, "escalate": True, "reason": reason}

    def create_visitor_pass(self, visit_date: str = "", visit_time: str = "", unit_id: str = "") -> dict[str, Any]:
        script_path = os.getenv("KAI_SMARTSERVA_TOOL_PATH", "").strip()
        if not script_path:
            repo_root = Path(__file__).resolve().parents[1]
            candidates = [
                repo_root / "integrations" / "smartserva" / "create_visitor_pass.py",
                repo_root / "smartserva" / "create_visitor_pass.py",
                repo_root.parent / "smartserva" / "create_visitor_pass.py",
                Path.cwd() / "integrations" / "smartserva" / "create_visitor_pass.py",
                Path.cwd() / "smartserva" / "create_visitor_pass.py",
            ]
            found = next((p for p in candidates if p.is_file()), None)
            script_path = str(found) if found else ""
        timeout_sec = int(os.getenv("KAI_SMARTSERVA_TOOL_TIMEOUT_SECONDS", "180"))

        if not script_path or not os.path.isfile(script_path):
            return {
                "ok": False,
                "error": "missing_smartserva_tool:set_KAI_SMARTSERVA_TOOL_PATH_or_place_file_at_integrations/smartserva/create_visitor_pass.py",
            }

        cmd = [
            "python3",
            script_path,
        ]
        if str(visit_date or "").strip():
            cmd.extend(["--date", str(visit_date).strip()])
        if str(visit_time or "").strip():
            cmd.extend(["--time", str(visit_time).strip()])
        if str(unit_id or "").strip():
            cmd.extend(["--unit-id", str(unit_id).strip()])

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "smartserva_tool_timeout"}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": f"smartserva_tool_exec_failed:{exc}"}

        output_blob = (proc.stdout or "").strip()
        err_blob = (proc.stderr or "").strip()
        merged = "\n".join([x for x in [output_blob, err_blob] if x]).strip()
        m = re.search(r"\{.*\}", merged, flags=re.S)
        payload: dict[str, Any] = {}
        if m:
            try:
                obj = json.loads(m.group(0))
                if isinstance(obj, dict):
                    payload = obj
            except Exception:
                payload = {}

        if proc.returncode != 0:
            return {
                "ok": False,
                "error": payload.get("error") if payload else "smartserva_tool_failed",
                "stdout": output_blob[:500],
                "stderr": err_blob[:500],
            }

        if not payload:
            return {"ok": False, "error": "smartserva_tool_invalid_output", "stdout": output_blob[:500]}

        if not payload.get("ok"):
            return {"ok": False, "error": payload.get("error", "smartserva_tool_failed"), "raw": payload}

        return {
            "ok": True,
            "visit_date": payload.get("visit_date"),
            "visit_time": payload.get("visit_time"),
            "visitor_name": payload.get("visitor_name"),
            "visitor_phone": payload.get("visitor_phone"),
            "visitor_id": payload.get("visitor_id"),
            "status": payload.get("status"),
            "visitor_pass_link": payload.get("visitor_pass_link"),
        }


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
