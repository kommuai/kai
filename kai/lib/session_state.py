import sqlite3, json, os, re
from datetime import datetime, timedelta, timezone

from kai.settings import get_settings

_s = get_settings()
MEMORY_SUMMARY_MAX_CHARS = _s.memory_summary_max_chars
MEMORY_TTL_PREFERENCES_DAYS = _s.memory_ttl_preferences_days
MEMORY_TTL_DEVICE_ACCOUNT_DAYS = _s.memory_ttl_device_account_days
MEMORY_TTL_TEMP_ISSUE_DAYS = _s.memory_ttl_temp_issue_days
SESSION_IDLE_HOURS = _s.session_idle_hours
SESSION_MAX_HISTORY_MESSAGES = _s.session_max_history_messages

DB_PATH = _s.session_db_path
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
    try:
        from kai.lib.session_search import ensure_message_index_schema

        ensure_message_index_schema()
    except Exception:
        pass

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
        "history": [],
        "session_summary": "",
        "session_started_at": None,
        "last_activity_at": None,
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


def _parse_iso_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _default_session_fields() -> dict:
    return {
        "lang": None,
        "frozen": False,
        "history": [],
        "session_summary": "",
        "session_started_at": None,
        "last_activity_at": None,
        "human_segment_open": False,
        "human_segment_messages": [],
        "human_segment_cw_conversation_id": "",
    }


def ensure_active_session(user_id: str) -> bool:
    """Start or continue a session. Returns True if the session was reset (idle > SESSION_IDLE_HOURS)."""
    if not user_id:
        return False
    now = datetime.now(timezone.utc)
    sess = get_session(user_id)
    last_dt = _parse_iso_dt(sess.get("last_activity_at"))
    idle_seconds = SESSION_IDLE_HOURS * 3600
    reset = bool(last_dt and (now - last_dt).total_seconds() > idle_seconds)
    if reset:
        preserved_lang = sess.get("lang")
        fresh = _default_session_fields()
        fresh["lang"] = preserved_lang
        # After SESSION_IDLE_HOURS with no activity, start fresh — bot resumes (no stuck LA freeze).
        sess = fresh
        sess["session_started_at"] = now.isoformat()
    elif not sess.get("session_started_at"):
        sess["session_started_at"] = now.isoformat()
    sess["last_activity_at"] = now.isoformat()
    save_session(user_id, sess)
    return reset


def touch_session_activity(user_id: str) -> None:
    if not user_id:
        return
    sess = get_session(user_id)
    sess["last_activity_at"] = datetime.now(timezone.utc).isoformat()
    save_session(user_id, sess)


# ----------------- State Updates -----------------
def set_lang(user_id: str, lang: str):
    sess = get_session(user_id)
    sess["lang"] = lang
    save_session(user_id, sess)

def freeze(user_id: str, frozen: bool):
    sess = get_session(user_id)
    sess["frozen"] = frozen
    if frozen:
        sess["frozen_at"] = _now_iso()
        if not sess.get("session_started_at"):
            sess["session_started_at"] = sess["frozen_at"]
    else:
        sess.pop("frozen_at", None)
    sess["last_activity_at"] = _now_iso()
    save_session(user_id, sess)


def auto_unfreeze_stale_handoff(user_id: str, *, idle_hours: int | None = None) -> bool:
    """End live-agent freeze after idle_hours (default SESSION_IDLE_HOURS, usually 24h).

    Uses ``frozen_at`` (set when handoff starts). Legacy sessions without it fall back to
    ``last_activity_at``. Returns True if the session was unfrozen.
    """
    if not user_id:
        return False
    sess = get_session(user_id)
    if not sess.get("frozen"):
        return False
    hours = SESSION_IDLE_HOURS if idle_hours is None else idle_hours
    threshold_s = max(1, hours) * 3600
    now = datetime.now(timezone.utc)
    frozen_at = _parse_iso_dt(sess.get("frozen_at")) or _parse_iso_dt(sess.get("last_activity_at"))
    if not frozen_at or (now - frozen_at).total_seconds() <= threshold_s:
        return False
    sess["frozen"] = False
    sess.pop("frozen_at", None)
    sess["human_segment_open"] = False
    save_session(user_id, sess)
    return True

# ----------------- Multi-Turn Memory -----------------
def add_message_to_history(user_id: str, role: str, text: str):
    """Append message to session history (full session window, capped at SESSION_MAX_HISTORY_MESSAGES)."""
    if not user_id:
        return
    ensure_active_session(user_id)
    sess = get_session(user_id)
    history = sess.get("history", [])
    history.append({"role": role, "text": text})
    cap = max(20, SESSION_MAX_HISTORY_MESSAGES)
    if len(history) > cap:
        history = history[-cap:]
    sess["history"] = history
    sess["last_activity_at"] = datetime.now(timezone.utc).isoformat()
    save_session(user_id, sess)
    try:
        from kai.lib.session_search import index_message

        index_message(user_id, role, (text or "").strip())
    except Exception:
        pass

def get_history(user_id: str) -> list[dict]:
    """All messages in the current session (same 24h idle window as ensure_active_session)."""
    if not user_id:
        return []
    ensure_active_session(user_id)
    return list(get_session(user_id).get("history") or [])


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
        default = _default_session_fields()
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


def snapshot_human_segment_for_learn(user_id: str) -> tuple[list[dict], str]:
    """Read current human segment without closing it."""
    sess = get_session(user_id)
    _ensure_human_segment_fields(sess)
    msgs = list(sess.get("human_segment_messages") or [])
    cw = str(sess.get("human_segment_cw_conversation_id") or "")
    return msgs, cw


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


