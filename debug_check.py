# debug_check.py  — Kai health/debug tool
import os, sys, io, csv, re, json
import requests, faiss, pickle
from pathlib import Path
from colorama import init, Fore, Style
from dotenv import load_dotenv

load_dotenv()

from config import (
    PORT, TZ_REGION, OFFICE_START, OFFICE_END,
    DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL,
    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER,
    CS_RECIPIENTS, AGENT_NUMBERS,
    SOP_DOC_URL, WARRANTY_CSV_URL,
    RAG_DIR, FAISS_DIR, ADMIN_TOKEN
)

# NEW: optional second warranty sheet (CSV)
EXTRA_WARRANTY_CSV_URL = os.getenv("EXTRA_WARRANTY_CSV_URL", "")

try:
    from deepseek_client import chat_completion
except Exception:
    chat_completion = None

try:
    from rag.rag import RAGEngine
except Exception:
    RAGEngine = None

RAG_INDEX = Path(FAISS_DIR) / "index.faiss"
RAG_META  = Path(FAISS_DIR) / "index.pkl"
SOP_JSON  = Path(RAG_DIR)  / "sop_data.json"

init(autoreset=True)

def mask(s, keep=3):
    if not s: return ""
    return s if len(s) <= keep*2 else s[:keep] + "…" + s[-keep:]

def header(t): print(Style.BRIGHT + f"\n=== {t} ===" + Style.RESET_ALL)
def ok(m):    print(Fore.GREEN + "OK  " + m + Style.RESET_ALL)
def bad(m):   print(Fore.RED   + "ERR " + m + Style.RESET_ALL)
def warn(m):  print(Fore.YELLOW+ "WARN " + m + Style.RESET_ALL)

def fetch_text(url):
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent":"Kai-Debug/1.0"})
        r.raise_for_status()
        return True, r.text, None
    except Exception as e:
        return False, "", str(e)

def fetch_csv(url):
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent":"Kai-Debug/1.0"})
        r.raise_for_status()
        content = r.content.decode("utf-8", errors="ignore")
        rows = list(csv.DictReader(io.StringIO(content)))
        return True, rows, None
    except Exception as e:
        return False, [], str(e)

def check_csv_url_format(label, url):
    if not url:
        warn(f"{label} not set")
        return False
    if "output=csv" not in url:
        warn(f"{label} is not CSV; use .../pub?gid=...&single=true&output=csv")
    ok(f"{label} set")
    return True

def main():
    print(Style.BRIGHT + "\n=== Kai Debug Check ===\n" + Style.RESET_ALL)

    # ---------- Env ----------
    header("Env")
    ok(f"Timezone            : {TZ_REGION}")
    ok(f"Office hours        : {OFFICE_START}:00–{OFFICE_END}:00")
    ok(f"Local server URL    : http://127.0.0.1:{PORT}")

    # ---------- DeepSeek ----------
    header("DeepSeek")
    ok(f"API key             : {'set' if DEEPSEEK_API_KEY else 'MISSING'} ({mask(DEEPSEEK_API_KEY)})")
    ok(f"Base URL            : {DEEPSEEK_BASE_URL}")
    ok(f"Model               : {DEEPSEEK_MODEL}")
    if DEEPSEEK_API_KEY and chat_completion:
        try:
            out = chat_completion("You only reply: OK.", "Ping?")
            ok(f"DeepSeek reply      : {out[:60]}")
        except Exception as e:
            warn(f"DeepSeek test failed: {e}")

    # ---------- Twilio ----------
    header("Twilio")
    ok(f"Account SID         : {mask(TWILIO_ACCOUNT_SID)}")
    ok(f"Auth Token          : {mask(TWILIO_AUTH_TOKEN)}")
    ok(f"From Number         : {TWILIO_WHATSAPP_NUMBER}")
    p = r"^whatsapp:\+\d{6,15}$"
    cs_ok = all(re.match(p, n or "") for n in CS_RECIPIENTS)
    ag_ok = all(re.match(p, n or "") for n in AGENT_NUMBERS)
    ok(f"CS_RECIPIENTS       : {len(CS_RECIPIENTS)} ({'ok' if cs_ok else 'format issue'})")
    ok(f"AGENT_NUMBERS       : {len(AGENT_NUMBERS)} ({'ok' if ag_ok else 'format issue'})")

    # ---------- SOP Doc ----------
    header("SOP (Published Google Doc)")
    if SOP_DOC_URL:
        ok("SOP_DOC_URL         : set")
        is_ok, text, err = fetch_text(SOP_DOC_URL)
        if not is_ok:
            bad(f"SOP fetch           : {err}")
        else:
            looks_html = "<html" in text.lower()
            if looks_html:
                # Published Google Doc is HTML — that’s fine; our parser strips tags
                ok("SOP response        : HTML (ok)")
            ok(f"SOP size            : {len(text)} chars")
            prev = "\n".join(text.strip().splitlines()[:5])
            print(Style.DIM + "Preview:\n" + prev[:300] + Style.RESET_ALL)
    else:
        warn("SOP_DOC_URL not set")

    # ---------- Warranty CSVs ----------
    header("Warranty CSVs")
    # Primary
    if check_csv_url_format("WARRANTY_CSV_URL", WARRANTY_CSV_URL):
        ok_csv, rows1, err1 = fetch_csv(WARRANTY_CSV_URL)
        if ok_csv:
            ok(f"Primary rows        : {len(rows1)}")
            if rows1:
                print(Style.DIM + "Primary cols: " + ", ".join(list(rows1[0].keys())) + Style.RESET_ALL)
        else:
            bad(f"Primary fetch       : {err1}")
    # Extra (new)
    if check_csv_url_format("EXTRA_WARRANTY_CSV_URL", EXTRA_WARRANTY_CSV_URL):
        ok_csv2, rows2, err2 = fetch_csv(EXTRA_WARRANTY_CSV_URL)
        if ok_csv2:
            ok(f"Extra rows          : {len(rows2)}")
            if rows2:
                print(Style.DIM + "Extra cols  : " + ", ".join(list(rows2[0].keys())) + Style.RESET_ALL)
        else:
            bad(f"Extra fetch         : {err2}")

    # ---------- RAG / FAISS ----------
    header("RAG / FAISS")
    ok(f"sop_data.json       : {'EXISTS' if Path(SOP_JSON).exists() else 'MISSING'}")
    ok(f"index.faiss         : {'EXISTS' if RAG_INDEX.exists() else 'MISSING'}")
    ok(f"index.pkl           : {'EXISTS' if RAG_META.exists() else 'MISSING'}")
    if RAG_INDEX.exists():
        try:
            idx = faiss.read_index(str(RAG_INDEX))
            ok(f"FAISS ntotal        : {idx.ntotal}")
        except Exception as e:
            bad(f"FAISS read          : {e}")
    if RAG_INDEX.exists() and RAG_META.exists() and RAGEngine:
        try:
            rag = RAGEngine(k=3)
            ctx = rag.build_context("What is Kommu?", topk=3)
            ok("RAGEngine search    : OK" if (ctx or "").strip() else "RAGEngine search    : empty")
        except Exception as e:
            bad(f"RAGEngine           : {e}")

    # ---------- Local server ----------
    header("Local server")
    try:
        r = requests.get(f"http://127.0.0.1:{PORT}/", timeout=3)
        ok(f"GET /               : {r.status_code}")
    except Exception as e:
        warn(f"GET / failed        : {e}")
    if ADMIN_TOKEN:
        try:
            r = requests.post(f"http://127.0.0.1:{PORT}/admin/refresh_sheets?token={ADMIN_TOKEN}", timeout=6)
            ok(f"POST /admin/refresh : {r.status_code}")
        except Exception as e:
            warn(f"/admin/refresh err  : {e}")

    print(Style.BRIGHT + "\nDebug complete.\n" + Style.RESET_ALL)

if __name__ == "__main__":
    main()
