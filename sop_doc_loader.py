import os, re, requests, json, base64
from config import (
    SOP_DOC_URL, GOOGLE_DOCS_SOP_DOC_ID
)

SOP_SYNC_START = "<!-- sop-sync:start -->"
SOP_SYNC_END = "<!-- sop-sync:end -->"

def fetch_sop_doc_text() -> str:
    if not SOP_DOC_URL:
        return ""
    r = requests.get(SOP_DOC_URL, timeout=30, headers={"User-Agent":"Kai/1.0"})
    r.raise_for_status()
    return r.text


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

def _clean_line(s: str) -> str:
    # collapse whitespace; strip bullets and numbering
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"^[•\-\*\d\)\(]+\s*", "", s)  
    return s

def _looks_question(line: str) -> bool:
    line = _clean_line(line)
    if not line: return False
    # question markers
    if re.match(r"^(q(uestion)?\.?\s*:)\s*", line, flags=re.I): return True
    if line.endswith("?") and 3 <= len(line) <= 200: return True
   
    if re.match(r"^(what|how|why|when|where|which|who)\b", line, flags=re.I): return True
    if re.match(r"^(apa|bagaimana|kenapa|bila|di mana|yang mana|siapa)\b", line, flags=re.I): return True
    return False

def _strip_q_prefix(line: str) -> str:
    line = _clean_line(line)
    line = re.sub(r"^(q(uestion)?\.?\s*:)\s*", "", line, flags=re.I)
    return line

def _is_answer_start(line: str) -> bool:
    return bool(re.match(r"^(a(nswer)?\.?\s*:)\s*", line, flags=re.I))

def _strip_a_prefix(line: str) -> str:
    return re.sub(r"^(a(nswer)?\.?\s*:)\s*", "", line, flags=re.I).strip()

def parse_qas_from_text(txt: str):
    """
    Robust parser:
      1) Prefer explicit 'Q:' / 'A:' or 'Question:' / 'Answer:' pairs
      2) Else, treat any line that looks like a question as Q, and collect following lines as A until next question
      3) Cleans bullets/numbering; ignores empty blocks
    Returns: list of {question, answer}
    """
    
    txt = txt.replace("\r", "")
    txt = re.sub(r"<br ?/?>", "\n", txt, flags=re.I)
    txt = re.sub(r"</p>\s*<p[^>]*>", "\n", txt, flags=re.I)
    txt = re.sub(r"<[^>]+>", "", txt)  # strip remaining tags
    lines = [l.strip() for l in txt.split("\n")]

    # Q/A markers
    qas = []
    q, a = None, []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if re.match(r"^(q(uestion)?\.?\s*:)\s*", line, flags=re.I):
            # flush previous
            if q and a:
                qa = {"question": _strip_q_prefix(q), "answer": _clean_line(" ".join(a))}
                if qa["question"] and qa["answer"]: qas.append(qa)
            q = line
            a = []
            continue
        if _is_answer_start(line):
            # start of answer 
            a = [_strip_a_prefix(line)]
            continue
        if q and (a or _is_answer_start(line)):
            # inside an answer
            a.append(line if not _is_answer_start(line) else _strip_a_prefix(line))
            continue

    if q and a:
        qa = {"question": _strip_q_prefix(q), "answer": _clean_line(" ".join(a))}
        if qa["question"] and qa["answer"]: qas.append(qa)
    
    if qas:
        return qas

    # heuristic — question-like line (ends with ? or starts with interrogative)
    qas = []
    cur_q, cur_a = None, []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if _looks_question(line):
            if cur_q and cur_a:
                qas.append({"question": _clean_line(cur_q), "answer": _clean_line(" ".join(cur_a))})
            cur_q = _strip_q_prefix(line)
            cur_a = []
        else:
            if cur_q:
                if _is_answer_start(line):
                    cur_a.append(_strip_a_prefix(line))
                else:
                    cur_a.append(line)

    if cur_q and cur_a:
        qas.append({"question": _clean_line(cur_q), "answer": _clean_line(" ".join(cur_a))})

    # small post-filter
    out = []
    for qa in qas:
        q = qa["question"].strip()
        a = qa["answer"].strip()
        if len(q) >= 3 and len(a) >= 3:
            out.append({"question": q, "answer": a})

    return out
