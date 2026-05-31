from __future__ import annotations

import base64
from datetime import datetime, timezone
import importlib.util
import json
import os
import re
from typing import Any

import requests

from config import GITHUB_BRANCH, GITHUB_REPO, TECH_ACTIVE_TAB_NAME, TECH_BACKLOG_SHEET_ID, TECH_BACKLOG_TAB_NAME


def _load_service_account_info() -> dict[str, Any]:
    raw = (os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON", "") or "").strip()
    if not raw:
        return {}
    if raw.startswith("{"):
        return json.loads(raw)
    if os.path.isfile(raw):
        with open(raw, "r", encoding="utf-8") as fh:
            return json.load(fh)
    try:
        return json.loads(base64.b64decode(raw).decode("utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def list_backlog_sheet_tabs() -> list[str]:
    if not TECH_BACKLOG_SHEET_ID:
        return []
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except Exception:
        return []
    info = _load_service_account_info()
    if not info:
        return []
    try:
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        sheets = build("sheets", "v4", credentials=creds, cache_discovery=False)
        meta = sheets.spreadsheets().get(spreadsheetId=TECH_BACKLOG_SHEET_ID).execute()
        return [sh.get("properties", {}).get("title", "") for sh in meta.get("sheets", []) if sh.get("properties")]
    except Exception:
        return []


def _extract_error_codes(text: str) -> list[str]:
    msg = text or ""
    patterns = [r"\b(?:error|err|code)\s*[:#-]?\s*([a-z0-9-]{3,20})\b", r"\b([0-9]{3,6})\b"]
    found: list[str] = []
    for pattern in patterns:
        for m in re.findall(pattern, msg, flags=re.IGNORECASE):
            code = str(m).upper().strip()
            if code and code not in found:
                found.append(code)
    return found[:5]


def summarize_issue(
    text: str,
    product_class: str = "",
    recent_user_messages: list[str] | None = None,
    *,
    device: str = "",
    car: str = "",
    category: str = "",
) -> str:
    recent_user_messages = recent_user_messages or []
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    latest_recent = [re.sub(r"\s+", " ", t).strip() for t in recent_user_messages if (t or "").strip()][-3:]
    error_codes = _extract_error_codes(" ".join([cleaned] + latest_recent))
    signals = [
        "fail",
        "failed",
        "not working",
        "still broken",
        "reboot",
        "restart",
        "hang",
        "stuck",
        "disconnect",
        "overheat",
    ]
    signal_hits = [s for s in signals if s in (cleaned.lower())][:4]
    parts = []
    dev = (device or "").strip()
    if dev:
        parts.append(f"Device={dev}")
    elif (product_class or "").strip():
        parts.append(f"Product={(product_class or '').strip()}")
    car_s = (car or "").strip()
    if car_s and car_s.lower() != "unknown":
        parts.append(f"Car={car_s}")
    cat_s = (category or "").strip()
    if cat_s and cat_s.lower() != "unknown":
        parts.append(f"Category={cat_s}")
    parts.append(f"Latest user report={cleaned[:320]}")
    if latest_recent:
        parts.append(f"Recent context={' | '.join(latest_recent)[:360]}")
    if error_codes:
        parts.append(f"Error codes={', '.join(error_codes)}")
    if signal_hits:
        parts.append(f"Failure signals={', '.join(signal_hits)}")
    return " ; ".join(parts)[:1200]


def _load_github_backlog_skill():
    return None


def github_repo_agentic_search(
    issue_text: str,
    *,
    branch: str | None = None,
    max_hits: int = 3,
    repo: str | None = None,
) -> dict[str, Any]:
    repo_name = (repo or GITHUB_REPO).strip().strip("/")
    branch = (branch or GITHUB_BRANCH).strip() or "main"
    skill = _load_github_backlog_skill()
    if skill:
        try:
            hits = skill.search_hits(issue_text, branch=branch, max_hits=max_hits)
            return {"ok": True, "branch": branch, "hits": hits}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "branch": branch, "hits": [], "error": f"skill_search_failed:{exc}"}
    tokens = [t for t in re.split(r"[^a-z0-9]+", issue_text.lower()) if len(t) >= 4][:6]
    if not tokens:
        return {"ok": True, "branch": branch, "hits": []}
    query = "+".join(tokens + [f"repo:{repo_name}"])
    headers = {}
    if os.getenv("SHADOU_GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.getenv('SHADOU_GITHUB_TOKEN')}"
    try:
        resp = requests.get(
            f"https://api.github.com/search/code?q={query}",
            headers=headers,
            timeout=15,
        )
        if not resp.ok:
            return {"ok": False, "branch": branch, "hits": [], "error": f"github_search_failed:{resp.status_code}"}
        items = (resp.json() or {}).get("items", [])[:max_hits]
        hits = []
        for item in items:
            path = item.get("path", "")
            repo_html = (
                ((item.get("repository") or {}).get("html_url")) or f"https://github.com/{repo_name}"
            ).rstrip("/")
            if not path:
                continue
            hits.append(
                {
                    "path": path,
                    "line": "",
                    "snippet": "",
                    "url": f"{repo_html}/blob/{branch}/{path}",
                    "source": "github-code-search",
                }
            )
        return {"ok": True, "branch": branch, "hits": hits}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "branch": branch, "hits": [], "error": f"search_exception:{exc}"}


def infer_possible_solution_from_github(issue_text: str) -> str:
    search = github_repo_agentic_search(issue_text, branch=GITHUB_BRANCH, max_hits=3)
    hits = search.get("hits", [])
    if not hits:
        return (
            f"No high-confidence code hit yet. Cross-check {GITHUB_REPO} branch {GITHUB_BRANCH} "
            "for diagnostics/recovery paths, reproduce on bench, then ship patch after validation."
        )
    refs = []
    for h in hits:
        path = h.get("path", "")
        url = h.get("url", "")
        if path and url:
            refs.append(f"{path} ({url})")
    joined = "; ".join(refs[:3])
    return (
        f"Cross-check suggests potential fix areas on {GITHUB_BRANCH}: {joined}. "
        "Validate root cause with logs, apply targeted patch, and include regression test before release."
    )[:1500]


def append_backlog_issue(
    *,
    device: str,
    car: str,
    issue_description: str,
    reproduction_steps: str,
) -> dict[str, Any]:
    if not TECH_BACKLOG_SHEET_ID:
        return {"ok": False, "error": "missing_tech_backlog_sheet_id"}
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"google_libs_missing:{exc}"}
    info = _load_service_account_info()
    if not info:
        return {"ok": False, "error": "invalid_service_account_info"}
    try:
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        sheets = build("sheets", "v4", credentials=creds, cache_discovery=False)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        row = [
            ts,
            (device or "Unknown").strip() or "Unknown",
            (car or "Unknown").strip() or "Unknown",
            (issue_description or "").strip(),
            (reproduction_steps or "").strip(),
        ]
        # Only 5 columns: timestamp, device, car, issue description, reproduction steps.
        range_name = f"'{TECH_BACKLOG_TAB_NAME}'!A:E"
        body = {"values": [row]}
        out = (
            sheets.spreadsheets()
            .values()
            .append(
                spreadsheetId=TECH_BACKLOG_SHEET_ID,
                range=range_name,
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body=body,
            )
            .execute()
        )
        return {"ok": True, "updatedRange": out.get("updates", {}).get("updatedRange", "")}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"append_failed:{exc}"}


def _terms(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", (text or "").lower()) if len(t) >= 3}


def find_similar_active_issue(issue: str, *, min_score: float = 0.28) -> dict[str, Any]:
    if not TECH_BACKLOG_SHEET_ID:
        return {"ok": False, "error": "missing_tech_backlog_sheet_id"}
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"google_libs_missing:{exc}"}
    info = _load_service_account_info()
    if not info:
        return {"ok": False, "error": "invalid_service_account_info"}
    try:
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        sheets = build("sheets", "v4", credentials=creds, cache_discovery=False)
        meta = sheets.spreadsheets().get(spreadsheetId=TECH_BACKLOG_SHEET_ID).execute()
        gid = ""
        for sh in meta.get("sheets", []):
            props = sh.get("properties", {})
            if props.get("title") == TECH_ACTIVE_TAB_NAME:
                gid = str(props.get("sheetId", ""))
                break

        rows = (
            sheets.spreadsheets()
            .values()
            .get(spreadsheetId=TECH_BACKLOG_SHEET_ID, range=f"'{TECH_ACTIVE_TAB_NAME}'!A:E")
            .execute()
            .get("values", [])
        )
        if len(rows) <= 1:
            return {"ok": True, "found": False}
        q = _terms(issue)
        best = {"score": 0.0}
        for idx, row in enumerate(rows[1:], start=2):
            # Column D (index 3) is the human-readable issue description.
            issue_cell = (row[3] or "").strip() if len(row) > 3 else ""
            if not issue_cell:
                continue
            t = _terms(issue_cell)
            score = len(q.intersection(t)) / max(1, len(q))
            if score > best.get("score", 0.0):
                best = {
                    "score": score,
                    "row": idx,
                    "issue": issue_cell,
                    "possible_solution": "",
                }
        if best.get("score", 0.0) < min_score:
            return {"ok": True, "found": False}
        tab_link = (
            f"https://docs.google.com/spreadsheets/d/{TECH_BACKLOG_SHEET_ID}/edit?gid={gid}#gid={gid}"
            if gid
            else f"https://docs.google.com/spreadsheets/d/{TECH_BACKLOG_SHEET_ID}/edit"
        )
        row_link = f"{tab_link}&range=A{best['row']}:E{best['row']}" if gid else tab_link
        return {
            "ok": True,
            "found": True,
            "match_issue": best["issue"],
            "match_solution": best.get("possible_solution", ""),
            "score": best["score"],
            "row": best["row"],
            "tab_link": tab_link,
            "row_link": row_link,
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"active_lookup_failed:{exc}"}
