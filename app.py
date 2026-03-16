# ----------------- Imports -----------------
from fastapi import FastAPI, Request, Query, Header, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import pytz, re, os, json, traceback, logging, sqlite3
from logging.handlers import RotatingFileHandler
import requests
from deep_translator import GoogleTranslator
from fastapi_utils.tasks import repeat_every

# ---- Kommu Internal Modules ----
from config import (
    TZ_REGION, OFFICE_START, OFFICE_END, PORT,
    SOP_DOC_URL, WARRANTY_CSV_URL,
    RAG_DIR, SOP_JSON_PATH, ADMIN_TOKEN,
    MIN_SUPPORTED_YEAR, MEMORY_DEPTH
)
from lang_detect import is_malay
from deepseek_client import chat_completion
from rag.rag import RAGEngine
from rag.rebuild_index_combined import rebuild as rebuild_rag
from sop_doc_loader import fetch_sop_doc_text, parse_qas_from_text
from google_sheets import (
    fetch_warranty_all, warranty_lookup_by_dongle, warranty_text_from_row
)
from session_state import (
    get_session, save_session, set_lang, freeze, update_reply_state,
    log_qna, init_db, set_last_intent, get_last_intent,
    add_message_to_history, get_history, reset_memory
)
from media_handler import handle_incoming_media, init_media_log

# ----------------- Logging -----------------
os.makedirs("logs", exist_ok=True)
handler = RotatingFileHandler("logs/kai.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
logging.basicConfig(level=logging.INFO, handlers=[handler])
log = logging.getLogger("kai")

# ----------------- App -----------------
app = FastAPI(title="Kai - Kommu Chatbot")

# Initialize databases
init_db()
init_media_log()

# Serve local /media folder for dashboard to access files
app.mount("/media", StaticFiles(directory="media"), name="media")



# ----------------- Constants -----------------
CAR_KEYWORDS = [
    "myvi", "alza", "ativa", "perodua", "proton", "s70", "x50", "x70",
    "honda", "city", "accord", "hrv", "crv", "toyota", "vios", "cross",
    "byd", "lexus", "kereta", "support", "compatible"
]
DROPOFF = "DROPOFF"
TESTDRIVE = "TD"
LIVEAGENT = ["KA1", "KA2", "LA"]

LIVEAGENT_TEXT = " | ".join(LIVEAGENT)

FOOTER_EN = f"\n\nFor Live Agent, type {LIVEAGENT_TEXT}"
FOOTER_BM = f"\n\nJika anda mahu bercakap dengan ejen yang sedia ada, taip {LIVEAGENT_TEXT}"


rag_sop = None

# ----------------- Utility Functions -----------------
def is_office_hours(now=None):
    tz = pytz.timezone(TZ_REGION)
    now = now or datetime.now(tz)
    return now.weekday() < 5 and OFFICE_START <= now.hour < OFFICE_END

def after_hours_suffix(lang="EN"):
    return ("\n\nPS: Sekarang di luar waktu pejabat."
            if lang == "BM"
            else "\n\nPS: We’re currently outside office hours. A live agent will follow up later.")

def norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()

def has_any(words, text: str) -> bool:
    return any(re.search(rf"\b{w}\b", text) for w in words)

def add_footer(conversation_id, answer: str, lang: str) -> str:
    footer = ""
    if len(get_history(conversation_id)) >= 7:
        footer = FOOTER_BM if lang == "BM" else FOOTER_EN
    
    return (answer or "").rstrip() + footer

def detect_car_support_query(text: str) -> bool:
    return any(k in text.lower() for k in CAR_KEYWORDS)

def extract_year(text: str) -> int | None:
    m = re.search(r"\b(19|20)\d{2}\b", text)
    return int(m.group()) if m else None

def parse_year_range(text: str):
    match = re.search(r"(\d{4})[–-](\d{4})", text)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None, None


# ----------------- RAG + Memory -----------------
def run_rag_dual(user_text: str, lang_hint: str = "EN", user_id: str | None = None) -> str:
    sys_prompt = (
        "You are Kai, Kommu’s polite and professional support assistant.\n"
        "- Always answer in a friendly and respectful tone.\n"
        "- Reply ONLY using the provided context, but do not mention this or \"Based on the provided context \" in your reply.\n"
        "- If context is found, avoid saying based on provided context. Likewise, if no context is found, do not mention anything about not finding context. Just say can't find information."
        "- If greetings are detected without any context, use \"Hi ! i'm Kai - Kommu Chatbot. I can help with price, support check, installation, office hours, part replacement, and test drives. Try: 'Buy Kommu', 'What is Kommu', 'How does it work', 'Office time', 'Test drive'.\"\n"
        "- Do NOT invent or make up links.\n"
        "- If user asks in Malay, reply in Malay.\n"
        "- Only include links from context or known sources.\n"
        "- If info not found, politely admit it.\n"
        f"- If you think the user is asking about scheduling drop offs, add a footnote \"For dropoffs, type {DROPOFF}, our staff will assist you shortly.\""
        f"- If you think the user is asking about test drives, add a footnote \"To schedule a test drive, type {TESTDRIVE}, our staff will assist you shortly.\""
        "- Do not mention the word context no matter what."
        "- No emojis. Max 5 links."
    )
    lang_instruction = "Jawab dalam BM dengan nada mesra." if lang_hint == "BM" else "Answer politely in English."

    # Conversation memory
    history_text = ""
    if user_id:
        history = get_history(user_id)
        if history:
            limited = history[-MEMORY_DEPTH:]
            history_text = "\n".join([f"{h['role']}: {h['text']}" for h in limited])

    # SOP RAG
    context = rag_sop.build_context(user_text, topk=4) if rag_sop else ""
    if context.strip():
        prompt = f"{history_text}\nUser: {user_text}\n\nContext:\n{context}\n\n{lang_instruction}"
        llm = chat_completion(sys_prompt, prompt)
        if llm:
            try:
                if lang_hint == "BM":
                    llm = GoogleTranslator(source="auto", target="ms").translate(llm)
            except Exception as e:
                log.warning(f"[Translate] BM translation failed: {e}")
            return llm.strip()

    if context.strip():
        prompt = f"{history_text}\nUser: {user_text}\n\nContext:\n{context}\n\n{lang_instruction}"
        llm = chat_completion(sys_prompt, prompt)
        if llm:
            try:
                if lang_hint == "BM":
                    llm = GoogleTranslator(source="auto", target="ms").translate(llm)
            except Exception as e:
                log.warning(f"[Translate] BM translation failed: {e}")
            return llm.strip()
    return ""

# ----------------- RAG Load -----------------
def load_rag():
    global rag_sop
    try:
        rag_sop = RAGEngine(k=4, base_dir=os.path.join(RAG_DIR, "faiss_index"))
        log.info("[Kai] SOP RAG loaded")
    except Exception as e:
        log.info(f"[Kai] SOP RAG not available: {e}")
        rag_sop = None

def refresh_sop_and_warranty():
    """
    Fetch SOP doc, rebuild RAG index, reload it,
    and refresh warranty cache.
    """
    try:
        txt = fetch_sop_doc_text()
        qas = parse_qas_from_text(txt)

        if qas:
            os.makedirs(RAG_DIR, exist_ok=True)

            with open(SOP_JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(qas, f, ensure_ascii=False, indent=2)

            rebuild_rag()
            load_rag()

            log.info(f"Loaded {len(qas)} SOP QAs")
        else:
            log.warning("No SOP QAs parsed")

        fetch_warranty_all()

        return {
            "ok": True,
            "qas_count": len(qas) if qas else 0,
        }

    except Exception as e:
        log.exception("Error refreshing SOP / warranty")
        return {
            "ok": False,
            "error": str(e),
        }

# ----------------- Scheduler -----------------
@app.on_event("startup")
def startup_event():
    log.info("[Kai] sessions.db initialized")
    refresh_sop_and_warranty()

@repeat_every(seconds=86400)
def auto_refresh():
    try:
        fetch_warranty_all()
        log.info("[AutoRefresh] Warranty refreshed")
    except Exception as e:
        log.error(f"[AutoRefresh] {e}")

# ----------------- Admin Endpoint -----------------
@app.post("/admin/reset_memory")
async def admin_reset_memory(request: Request):
    user_id = request.query_params.get("user_id") or (await request.form()).get("user_id")
    reset_memory(user_id)
    log.info(f"[ADMIN] Memory reset for {user_id}")
    return PlainTextResponse("Memory reset completed")

@app.post("/admin/refresh-sop")
def refresh_sop_endpoint():
    return refresh_sop_and_warranty()

def list_sessions():
    conn = sqlite3.connect("sessions.db")
    cur = conn.cursor()
    cur.execute("SELECT user_id, data FROM sessions")
    rows = []
    for user_id, data in cur.fetchall():
        try:
            sess = json.loads(data)
            hist = sess.get("history", [])
            last = hist[-1]["text"] if hist else ""
            rows.append({
                "user_id": user_id,
                "lastMessage": last,
                "frozen": sess.get("frozen", False),
                "lang": sess.get("lang", "EN")
            })
        except Exception:
            pass
    conn.close()
    return rows

def get_chat_history(user_id: str):
    conn = sqlite3.connect("sessions.db")
    cur = conn.cursor()
    cur.execute("SELECT data FROM sessions WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return []
    sess = json.loads(row[0])
    hist = sess.get("history", [])
    return [{"sender": h.get("role", "bot"), "content": h.get("text", "")} for h in hist]

# ----------------- N8N (Main Entry) -----------------

@app.post("/agent/message")
async def agent_message(request: Request):
    data = await request.json()

    if not data:
        raise HTTPException(400, "Invalid n8n payload")

    # ---- extract fields ----
    text = data.get("content", "").strip()
    if not text:
        return {"ok": True}  # ignore empty messages
    
    # Update from user_id to conversation_id. In session_state.py, it is still user_id
    conversation_id = data.get("phone_number", "unknown")
    # user_name = data.get("name")

    # ---- inbound log ----
    log.info( "[Kai] IN conv=%s type=text text=%s", conversation_id, text)
    lower = norm(text)

    sess = get_session(conversation_id)
    lang = "BM" if is_malay(text) else "EN"
    set_lang(conversation_id, lang)
    aft = not is_office_hours()
    add_message_to_history(conversation_id, "user", text)
    print(lang)
    print(conversation_id)
    print(sess)


    if text == DROPOFF and not sess.get("frozen") and not sess.get("handover"):
        sess["frozen"] = True
        save_session(conversation_id,sess)
        msg_out = ("Please provide the date and time for the dropoff. Our staff will assist you soon. Type *resume* to continue with the bot."
                    if lang=="EN" else
                    "Sila berikan tarikh dan masa untuk penghantaran. Ejen kami akan membantu anda sebentar lagi. Taip *resume* untuk teruskan.")
        
        if aft: msg_out += after_hours_suffix(lang)
            
        return {
            "type": "handover",
            "message": msg_out,
            "next_state": "human",
        }    


    if text in LIVEAGENT and not sess.get("frozen") and not sess.get("handover"):
        sess["frozen"] = True
        save_session(conversation_id,sess)
        msg_out = ("A live agent will assist you soon. Type *resume* to continue with the bot."
                    if lang=="EN" else
                    "Ejen kami akan membantu anda. Taip *resume* untuk teruskan.")
        
        if aft: msg_out += after_hours_suffix(lang)
            
        return {
            "type": "handover",
            "message": msg_out,
            "next_state": "human",
        }

    # -------- Live Agent Handling --------
    if sess.get("frozen"):
        if lower in {"resume","unfreeze","sambung"}:
            freeze(conversation_id, False)
            msg_out = "Bot resumed. How can I help?" if lang=="EN" else "Bot disambung semula. Ada apa saya boleh bantu?"
            return {
                "type": "reply",
                "message": msg_out,
                "next_state": "bot",
            }

        return {
            "type": "frozen",
            "message": "",
            "next_state": "human",
        }


    # -------- Warranty Lookup --------
    if 6 <= len(text) <= 20:
        row = warranty_lookup_by_dongle(text)
        if row:
            msg_out = (f"Warranty status: {warranty_text_from_row(row)}"
                        if lang=="EN" else
                        f"Status waranti: {warranty_text_from_row(row)}")
            return {
                "type": "reply",
                "message": add_footer(conversation_id, msg_out, lang),
                "next_state": "bot",
            }

    # -------- Car Support Logic --------
    if detect_car_support_query(text):
        answer = run_rag_dual(text, lang_hint=lang, user_id=conversation_id)
        lower_ans = answer.lower() if answer else ""
        year_in_text = extract_year(text)
        sop_years = parse_year_range(answer)

        if any(k in lower_ans for k in CAR_KEYWORDS):
            if sop_years != (None, None) and year_in_text:
                start, end = sop_years
                if year_in_text < start or year_in_text > end:
                    msg_out = (f"Sorry, the {year_in_text} model is not supported. KommuAssist supports {start}–{end} variants only."
                                if lang=="EN" else
                                f"Maaf, model tahun {year_in_text} tidak disokong. KommuAssist hanya menyokong varian {start}–{end} sahaja.")
                    add_message_to_history(conversation_id, "bot", msg_out)
                    return {
                            "type": "reply",
                            "message": add_footer(conversation_id, msg_out, lang),
                            "next_state": "bot",
                        }
            add_message_to_history(conversation_id, "bot", answer)
            return {
                "type": "reply",
                "message": add_footer(conversation_id, answer, lang),
                "next_state": "bot",
            }
        msg_out = ("I'm not sure about that car. Does it have Adaptive Cruise Control (ACC) and Lane Keep Assist (LKA)?"
                    if lang=="EN"
                    else "Saya tidak pasti tentang kereta itu. Adakah ia mempunyai sistem Adaptive Cruise Control (ACC) dan Lane Keep Assist (LKA)?")
        set_last_intent(conversation_id, "car_unknown")
        add_message_to_history(conversation_id, "bot", msg_out)
        return {
            "type": "reply",
            "message": add_footer(conversation_id, msg_out, lang),
            "next_state": "bot",
        }

    # -------- Fallback (General) --------
    answer = run_rag_dual(text, lang_hint=lang, user_id=conversation_id)
    if answer:
        add_message_to_history(conversation_id, "bot", answer)
        return {
            "type": "reply",
            "message": add_footer(conversation_id, answer, lang),
            "next_state": "bot",
        }


        msg_out = ("I can help with pricing, installation, office hours, warranty, and test drives."
                if lang=="EN" else
                "Saya boleh bantu dengan harga, pemasangan, waktu pejabat, waranti, dan pandu uji.")
        
        add_message_to_history(conversation_id, "bot", msg_out)
        return {
            "type": "reply",
            "message": add_footer(conversation_id, msg_out, lang),
            "next_state": "bot",
        }

    return {
        "type": "reply",
        "message": "Retry please",
        "next_state": "bot",
    }