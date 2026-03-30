import sqlite3, json, os, re
from datetime import datetime, timedelta, timezone
from config import (
    MEMORY_DEPTH,
    MEMORY_SUMMARY_MAX_CHARS,
    MEMORY_TTL_PREFERENCES_DAYS,
    MEMORY_TTL_DEVICE_ACCOUNT_DAYS,
    MEMORY_TTL_TEMP_ISSUE_DAYS,
)

DB_PATH = os.getenv("SESSION_DB_PATH", "data/sessions.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# ----------------- Database Init -----------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        user_id TEXT PRIMARY KEY,
        data TEXT
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS memory_facts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        fact_type TEXT NOT NULL,
        fact_key TEXT NOT NULL,
        fact_value TEXT NOT NULL,
        source TEXT NOT NULL,
        last_seen_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        UNIQUE(user_id, fact_type, fact_key)
    )
    """)
    c.execute("DROP TABLE IF EXISTS faq_candidates")
    conn.commit()
    conn.close()

# ----------------- Core Session Ops -----------------
def get_session(user_id: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT data FROM sessions WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        try:
            return json.loads(row[0])
        except Exception:
            return {}
    # Default session structure
    return {
        "lang": None,
        "frozen": False,
        "reply_count": 0,
        "greeted": False,
        "last_intent": None,
        "history": [],
        "session_summary": "",
        "human_segment_open": False,
        "human_segment_messages": [],
        "human_segment_cw_conversation_id": "",
    }

def save_session(user_id: str, data: dict):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("REPLACE INTO sessions (user_id, data) VALUES (?,?)", (user_id, json.dumps(data)))
    conn.commit()
    conn.close()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _expires_iso(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()

# ----------------- State Updates -----------------
def set_lang(user_id: str, lang: str):
    sess = get_session(user_id)
    sess["lang"] = lang
    save_session(user_id, sess)

def freeze(user_id: str, frozen: bool):
    sess = get_session(user_id)
    sess["frozen"] = frozen
    save_session(user_id, sess)

def update_reply_state(user_id: str):
    sess = get_session(user_id)
    sess["reply_count"] = sess.get("reply_count", 0) + 1
    save_session(user_id, sess)

def log_qna(user_id: str, q: str, a: str):
    sess = get_session(user_id)
    logs = sess.get("logs", [])
    logs.append({"q": q, "a": a, "t": datetime.utcnow().isoformat()})
    sess["logs"] = logs[-50:]  # Keep last 50 pairs
    save_session(user_id, sess)

def set_last_intent(user_id: str, intent: str | None):
    sess = get_session(user_id)
    sess["last_intent"] = intent
    save_session(user_id, sess)

def get_last_intent(user_id: str):
    sess = get_session(user_id)
    return sess.get("last_intent")

# ----------------- Multi-Turn Memory -----------------
def add_message_to_history(user_id: str, role: str, text: str):
    """Append message to session history, keeping only MEMORY_DEPTH turns."""
    sess = get_session(user_id)
    history = sess.get("history", [])
    history.append({"role": role, "text": text})
    if len(history) > MEMORY_DEPTH:
        history = history[-MEMORY_DEPTH:]
    sess["history"] = history
    save_session(user_id, sess)

def get_history(user_id: str):
    """Retrieve the recent conversation history."""
    sess = get_session(user_id)
    return sess.get("history", [])


def update_session_summary(user_id: str, role: str, text: str):
    """Maintain always-on running summary for active conversation."""
    sess = get_session(user_id)
    summary = (sess.get("session_summary") or "").strip()
    role_prefix = "User" if role == "user" else "Bot"
    addition = f"{role_prefix}: {text.strip()}"
    if not summary:
        new_summary = addition
    else:
        new_summary = f"{summary}\n{addition}"
    # Keep tail to avoid unbounded growth.
    if len(new_summary) > MEMORY_SUMMARY_MAX_CHARS:
        new_summary = new_summary[-MEMORY_SUMMARY_MAX_CHARS:]
    sess["session_summary"] = new_summary
    save_session(user_id, sess)


def get_session_summary(user_id: str) -> str:
    return (get_session(user_id).get("session_summary") or "").strip()


def prune_expired_memory_facts(user_id: str | None = None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = _now_iso()
    if user_id:
        c.execute("DELETE FROM memory_facts WHERE user_id=? AND expires_at < ?", (user_id, now))
    else:
        c.execute("DELETE FROM memory_facts WHERE expires_at < ?", (now,))
    conn.commit()
    conn.close()


def upsert_memory_fact(
    user_id: str,
    fact_type: str,
    fact_key: str,
    fact_value: str,
    source: str,
    ttl_days: int,
):
    if not user_id or not fact_type or not fact_key or not fact_value:
        return
    prune_expired_memory_facts(user_id)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO memory_facts (user_id, fact_type, fact_key, fact_value, source, last_seen_at, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, fact_type, fact_key)
        DO UPDATE SET
          fact_value=excluded.fact_value,
          source=excluded.source,
          last_seen_at=excluded.last_seen_at,
          expires_at=excluded.expires_at
        """,
        (user_id, fact_type, fact_key, fact_value, source, _now_iso(), _expires_iso(ttl_days)),
    )
    conn.commit()
    conn.close()


def get_memory_facts(user_id: str, fact_type: str | None = None) -> list[dict]:
    prune_expired_memory_facts(user_id)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if fact_type:
        c.execute(
            """
            SELECT fact_type, fact_key, fact_value, source, last_seen_at, expires_at
            FROM memory_facts WHERE user_id=? AND fact_type=?
            ORDER BY last_seen_at DESC
            """,
            (user_id, fact_type),
        )
    else:
        c.execute(
            """
            SELECT fact_type, fact_key, fact_value, source, last_seen_at, expires_at
            FROM memory_facts WHERE user_id=?
            ORDER BY last_seen_at DESC
            """,
            (user_id,),
        )
    rows = c.fetchall()
    conn.close()
    return [
        {
            "fact_type": r[0],
            "fact_key": r[1],
            "fact_value": r[2],
            "source": r[3],
            "last_seen_at": r[4],
            "expires_at": r[5],
        }
        for r in rows
    ]


def _extract_name(text: str) -> str:
    m = re.search(r"\b(?:my name is|i am|i'm)\s+([A-Za-z][A-Za-z .'-]{1,40})\b", text, flags=re.I)
    return (m.group(1).strip() if m else "")


def _extract_car(text: str) -> str:
    m = re.search(r"\b(my car is|i drive|i own)\s+([A-Za-z0-9][A-Za-z0-9 .-]{2,60})\b", text, flags=re.I)
    return (m.group(2).strip() if m else "")


def _extract_purchase_state(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ("already purchased", "i bought", "i have purchased", "paid")):
        return "purchased"
    if any(k in t for k in ("want to buy", "planning to buy", "considering to buy")):
        return "considering_purchase"
    return ""


def _extract_lang_pref(text: str) -> str:
    t = text.lower()
    if "reply in bm" in t or "bahasa melayu" in t:
        return "BM"
    if "reply in english" in t or "english please" in t:
        return "EN"
    return ""


def _extract_issue_state(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ("error", "issue", "not working", "cannot", "can't", "problem")):
        return t[:160]
    return ""


def extract_and_store_facts(user_id: str, text: str, source: str = "user"):
    """Store durable facts only; ignore generic chatter."""
    if not user_id or not text.strip():
        return
    # Device/account anchor: phone number as account key.
    upsert_memory_fact(
        user_id=user_id,
        fact_type="device_account",
        fact_key="phone_number",
        fact_value=user_id,
        source=source,
        ttl_days=MEMORY_TTL_DEVICE_ACCOUNT_DAYS,
    )

    name = _extract_name(text)
    if name:
        upsert_memory_fact(user_id, "identity", "name", name, source, MEMORY_TTL_PREFERENCES_DAYS)

    lang_pref = _extract_lang_pref(text)
    if lang_pref:
        upsert_memory_fact(user_id, "preference", "language", lang_pref, source, MEMORY_TTL_PREFERENCES_DAYS)

    car = _extract_car(text)
    if car:
        upsert_memory_fact(user_id, "device_account", "car_owned", car, source, MEMORY_TTL_DEVICE_ACCOUNT_DAYS)

    purchase_state = _extract_purchase_state(text)
    if purchase_state:
        upsert_memory_fact(
            user_id, "device_account", "purchase_state", purchase_state, source, MEMORY_TTL_DEVICE_ACCOUNT_DAYS
        )

    issue_state = _extract_issue_state(text)
    if issue_state:
        upsert_memory_fact(user_id, "temporary_issue", "active_issue", issue_state, source, MEMORY_TTL_TEMP_ISSUE_DAYS)

# ----------------- Memory Reset Helpers -----------------
def reset_memory(user_id: str | None = None):
    """
    Reset memory for a specific user or all users.
    - If user_id provided: reset that user's data to defaults.
    - If None: clears all sessions (admin bulk reset).
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if user_id:
        default = {
            "lang": None,
            "frozen": False,
            "reply_count": 0,
            "greeted": False,
            "last_intent": None,
            "history": [],
            "session_summary": "",
            "human_segment_open": False,
            "human_segment_messages": [],
            "human_segment_cw_conversation_id": "",
        }
        c.execute("REPLACE INTO sessions (user_id, data) VALUES (?,?)", (user_id, json.dumps(default)))
        c.execute("DELETE FROM memory_facts WHERE user_id=?", (user_id,))
    else:
        c.execute("DELETE FROM sessions")
        c.execute("DELETE FROM memory_facts")
    conn.commit()
    conn.close()

# ----------------- Utility -----------------
def get_all_user_ids():
    """Return list of all active session user_ids (for admin view/logging)."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id FROM sessions")
    rows = [r[0] for r in c.fetchall()]
    conn.close()
    return rows


def _ensure_human_segment_fields(sess: dict) -> None:
    sess.setdefault("human_segment_open", False)
    sess.setdefault("human_segment_messages", [])
    sess.setdefault("human_segment_cw_conversation_id", "")


def start_human_segment(user_id: str, cw_conversation_id: str | None = None) -> None:
    """Begin capturing turns for post-handback FAQ learning."""
    sess = get_session(user_id)
    _ensure_human_segment_fields(sess)
    sess["human_segment_open"] = True
    sess["human_segment_messages"] = []
    if cw_conversation_id:
        sess["human_segment_cw_conversation_id"] = str(cw_conversation_id)
    else:
        sess["human_segment_cw_conversation_id"] = ""
    save_session(user_id, sess)


def append_human_segment_turn(user_id: str, role: str, text: str) -> None:
    """Append one line to the live-agent window (user / assistant / human_agent)."""
    sess = get_session(user_id)
    _ensure_human_segment_fields(sess)
    if not sess.get("human_segment_open"):
        return
    msg = (text or "").strip()
    if not msg:
        return
    hist = sess.get("human_segment_messages") or []
    hist.append({"role": role, "text": msg, "ts": _now_iso()})
    sess["human_segment_messages"] = hist[-400:]
    save_session(user_id, sess)


def pop_human_segment_for_learn(user_id: str) -> tuple[list[dict], str]:
    """Close the segment and return (messages, chatwoot_conversation_id)."""
    sess = get_session(user_id)
    _ensure_human_segment_fields(sess)
    msgs = list(sess.get("human_segment_messages") or [])
    cw = str(sess.get("human_segment_cw_conversation_id") or "")
    sess["human_segment_open"] = False
    sess["human_segment_messages"] = []
    sess["human_segment_cw_conversation_id"] = ""
    save_session(user_id, sess)
    return msgs, cw


