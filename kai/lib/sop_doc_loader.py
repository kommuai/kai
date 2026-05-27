import json
import os
import base64

from config import GOOGLE_DOCS_SOP_DOC_ID

SOP_SYNC_START = "<!-- sop-sync:start -->"
SOP_SYNC_END = "<!-- sop-sync:end -->"


def _load_service_account_info() -> dict:
    raw = (os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON", "") or "").strip()
    if not raw:
        return {}
    if raw.startswith("{"):
        return json.loads(raw)
    if os.path.isfile(raw):
        with open(raw, "r", encoding="utf-8") as fh:
            return json.load(fh)
    try:
        decoded = base64.b64decode(raw).decode("utf-8")
        return json.loads(decoded)
    except Exception:  # noqa: BLE001
        return {}


def fetch_sop_sync_region_from_google_doc() -> str:
    """Read marker-bounded sop-sync region directly from Google Docs API."""
    if not GOOGLE_DOCS_SOP_DOC_ID:
        return ""
    info = _load_service_account_info()
    if not info:
        return ""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except Exception:
        return ""
    try:
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/documents.readonly"]
        )
        docs = build("docs", "v1", credentials=creds, cache_discovery=False)
        doc = docs.documents().get(documentId=GOOGLE_DOCS_SOP_DOC_ID).execute()
        text = ""
        for block in doc.get("body", {}).get("content", []):
            para = block.get("paragraph") or {}
            for el in para.get("elements", []):
                tr = (el.get("textRun") or {}).get("content")
                if tr:
                    text += tr
        if SOP_SYNC_START not in text or SOP_SYNC_END not in text:
            return ""
        start = text.index(SOP_SYNC_START) + len(SOP_SYNC_START)
        end = text.index(SOP_SYNC_END, start)
        return text[start:end].strip("\n")
    except Exception:
        return ""
