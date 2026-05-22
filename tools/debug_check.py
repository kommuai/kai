# debug_check.py  — Kai health/debug tool
import os, io, csv, re
import requests
from pathlib import Path
from colorama import init, Fore, Style
from dotenv import load_dotenv

load_dotenv()

from config import (
    PORT, TZ_REGION, OFFICE_START, OFFICE_END,
    DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL,
    SOP_DOC_URL, WARRANTY_CSV_URL,
    AGENT_WORKSPACE, MASTER_FAQ_PATH, SOP_SYNC_STATE_PATH,
)

# NEW: optional second warranty sheet (CSV)
EXTRA_WARRANTY_CSV_URL = os.getenv("EXTRA_WARRANTY_CSV_URL", "")

try:
    from kai.lib.deepseek_client import chat_completion
except Exception:
    chat_completion = None

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

    # ---------- Chat channel env ----------
    header("Channel env (optional)")
    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    twilio_from = os.getenv("TWILIO_WHATSAPP_NUMBER", "")
    cs = [x.strip() for x in os.getenv("CS_RECIPIENTS", "").split(",") if x.strip()]
    agents = [x.strip() for x in os.getenv("AGENT_NUMBERS", "").split(",") if x.strip()]
    ok(f"TWILIO_ACCOUNT_SID  : {mask(twilio_sid) or 'not set'}")
    ok(f"TWILIO_AUTH_TOKEN   : {mask(twilio_token) or 'not set'}")
    ok(f"TWILIO_WHATSAPP_NUM : {twilio_from or 'not set'}")
    p = r"^whatsapp:\+\d{6,15}$"
    cs_ok = all(re.match(p, n or "") for n in cs)
    ag_ok = all(re.match(p, n or "") for n in agents)
    ok(f"CS_RECIPIENTS       : {len(cs)} ({'ok' if cs_ok else 'format issue'})")
    ok(f"AGENT_NUMBERS       : {len(agents)} ({'ok' if ag_ok else 'format issue'})")

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

    # ---------- FAQ / compiled knowledge (active runtime) ----------
    header("FAQ / compiled knowledge")
    ok(f"master_faq.md       : {'EXISTS' if Path(MASTER_FAQ_PATH).exists() else 'MISSING'}")
    compiled = Path(AGENT_WORKSPACE) / "compiled"
    kb = compiled / "kb_chunks.jsonl"
    ok(f"compiled/kb_chunks.jsonl : {'EXISTS' if kb.exists() else 'MISSING'}")
    intents = compiled / "intents.json"
    if intents.exists():
        ok("compiled/intents.json   : EXISTS (optional debug artifact)")
    ok(f"sop_sync_state.json : {'EXISTS' if Path(SOP_SYNC_STATE_PATH).exists() else 'MISSING'}")

    # ---------- Local server ----------
    header("Local server")
    try:
        r = requests.get(f"http://127.0.0.1:{PORT}/", timeout=3)
        ok(f"GET /               : {r.status_code}")
    except Exception as e:
        warn(f"GET / failed        : {e}")
    try:
        r = requests.post(f"http://127.0.0.1:{PORT}/admin/refresh-sop", timeout=8)
        ok(f"POST /admin/refresh-sop : {r.status_code}")
    except Exception as e:
        warn(f"/admin/refresh-sop err  : {e}")

    print(Style.BRIGHT + "\nDebug complete.\n" + Style.RESET_ALL)

if __name__ == "__main__":
    main()
