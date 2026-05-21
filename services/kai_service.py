from datetime import datetime
from functools import lru_cache
import html
import logging
import os
import re
from typing import Any

import pytz
import requests
from deep_translator import GoogleTranslator

from config import (
    VEHICLE_SUPPORT_HTTP_TIMEOUT_SECONDS,
    VEHICLE_SUPPORT_OFFICIAL_URL,
    TZ_REGION,
    OFFICE_START,
    OFFICE_END,
    RAG_DIR,
    MEMORY_DEPTH,
)
from core.prompt_loader import build_rag_system_prompt
from core.sop_ingest import ingest_sop_qas
from deepseek_client import chat_completion
from google_sheets import fetch_warranty_all, warranty_lookup_by_dongle, warranty_text_from_row
from lang_detect import is_malay
from media_handler import init_media_log
from rag.rag import RAGEngine
from rag.rebuild_index_combined import rebuild as rebuild_rag
from session_state import (
    add_message_to_history,
    append_human_segment_turn,
    extract_and_store_facts,
    freeze,
    get_history,
    get_memory_facts,
    get_session,
    get_session_summary,
    init_db,
    reset_memory,
    save_session,
    set_lang,
    set_last_intent,
    start_human_segment,
    update_session_summary,
)
from services.chatwoot_handover import extract_chatwoot_conversation_id
from support_runtime.faq_learn import schedule_faq_learn_after_handback
log = logging.getLogger("kai")

CAR_KEYWORDS = [
    "myvi",
    "alza",
    "ativa",
    "perodua",
    "proton",
    "s70",
    "x50",
    "x70",
    "honda",
    "city",
    "accord",
    "hrv",
    "crv",
    "toyota",
    "vios",
    "cross",
    "byd",
    "lexus",
    "kereta",
    "support",
    "compatible",
]
DROPOFF = "DROPOFF"
TESTDRIVE = "TD"
LIVEAGENT = ["LA"]
FOOTER_EN = "\n\nFor Live Agent, type LA"
FOOTER_BM = "\n\nJika anda mahu bercakap dengan ejen yang sedia ada, taip LA"
SUPPORTED_VEHICLE_JSON_URL = (
    "https://raw.githubusercontent.com/kommuai/bukapilot/snapshot/selfdrive/car/supported_vehicle.json"
)
_SUPPORT_QUERY_STOPWORDS = {
    "is",
    "my",
    "car",
    "support",
    "supported",
    "can",
    "does",
    "have",
    "with",
    "the",
    "and",
    "for",
    "kommu",
    "kommuassist",
}


def _strip_html(raw: str) -> str:
    txt = html.unescape(raw or "")
    txt = re.sub(r"(?is)<script.*?>.*?</script>", " ", txt)
    txt = re.sub(r"(?is)<style.*?>.*?</style>", " ", txt)
    txt = re.sub(r"(?s)<[^>]+>", " ", txt)
    return re.sub(r"\s+", " ", txt).strip()


def strip_bold_markdown_wrapping_around_urls(text: str) -> str:
    """Remove **bold** wrapping only around http(s) URLs (LLM habit breaks tappable links in WhatsApp, etc.)."""
    if not text:
        return text
    return re.sub(r"\*\*(https?://[^\s*]+)\*\*", r"\1", text)


@lru_cache(maxsize=1)
def _official_support_text() -> str:
    try:
        resp = requests.get(VEHICLE_SUPPORT_OFFICIAL_URL, timeout=VEHICLE_SUPPORT_HTTP_TIMEOUT_SECONDS)
        if not resp.ok:
            return ""
        return _strip_html(resp.text)
    except Exception:
        return ""


def _extract_support_evidence(user_text: str, support_corpus: str) -> str:
    corpus = (support_corpus or "").lower()
    if not corpus:
        return ""
    query = (user_text or "").lower()
    tokens = [
        tok
        for tok in re.split(r"[^a-z0-9]+", query)
        if len(tok) >= 3 and tok not in _SUPPORT_QUERY_STOPWORDS
    ]
    if not tokens:
        return ""
    year_match = re.search(r"\b(19|20)\d{2}\b", query)
    year = year_match.group(0) if year_match else ""

    def _year_in_sentence(sentence_l: str, y: str) -> bool:
        if not y:
            return True
        try:
            yi = int(y)
        except ValueError:
            return False
        if y in sentence_l:
            return True
        for a, b in re.findall(r"((?:19|20)\d{2})\s*[–-]\s*((?:19|20)\d{2})", sentence_l):
            if int(a) <= yi <= int(b):
                return True
        return False

    best_score = 0
    best_sentence = ""
    for sentence in re.split(r"(?<=[\.\!\?])\s+", support_corpus):
        s = sentence.strip()
        if not s:
            continue
        sl = s.lower()
        token_hits = sum(1 for tok in tokens if tok in sl)
        if token_hits == 0:
            continue
        year_hit = _year_in_sentence(sl, year)
        score = token_hits + (2 if year_hit else 0)
        # Require fairly specific evidence to avoid false positives.
        if year and not year_hit:
            continue
        if token_hits < 2 and not year_hit:
            continue
        if score > best_score:
            best_score = score
            best_sentence = s
    return best_sentence


def _expand_years(raw: str) -> set[int]:
    text = str(raw or "")
    years: set[int] = set()
    for a, b in re.findall(r"((?:19|20)\d{2})\s*[–-]\s*((?:19|20)\d{2})", text):
        years.update(range(int(a), int(b) + 1))
    for y in re.findall(r"\b((?:19|20)\d{2})\b", text):
        years.add(int(y))
    return {y for y in years if 1980 <= y <= 2035}


@lru_cache(maxsize=1)
def _official_supported_vehicles() -> list[dict[str, Any]]:
    try:
        resp = requests.get(SUPPORTED_VEHICLE_JSON_URL, timeout=VEHICLE_SUPPORT_HTTP_TIMEOUT_SECONDS)
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
        years = _expand_years(str(row.get("year") or ""))
        rows.append(
            {
                "brand": brand,
                "model": model,
                "name": f"{brand} {model}".strip(),
                "years": years,
            }
        )
    return rows


def _match_supported_vehicle_query(user_text: str, vehicles: list[dict[str, Any]]) -> dict[str, Any] | None:
    query = (user_text or "").lower()
    if not query:
        return None
    year_match = re.search(r"\b(19|20)\d{2}\b", query)
    query_year = int(year_match.group(0)) if year_match else None
    query_tokens = [
        tok
        for tok in re.split(r"[^a-z0-9]+", query)
        if len(tok) >= 3 and tok not in _SUPPORT_QUERY_STOPWORDS
    ]
    if not query_tokens:
        return None

    best: dict[str, Any] | None = None
    best_score = -1
    for row in vehicles:
        name_l = str(row.get("name") or "").lower()
        if not name_l:
            continue
        token_hits = sum(1 for tok in query_tokens if tok in name_l)
        if token_hits < 2:
            continue
        years = row.get("years") or set()
        if query_year is not None and years and query_year not in years:
            continue
        score = token_hits + (2 if query_year is not None and query_year in years else 0)
        if score > best_score:
            best_score = score
            best = row
    return best


class KaiService:
    def __init__(self) -> None:
        self.rag_sop: RAGEngine | None = None
        init_db()
        init_media_log()

    def is_office_hours(self, now=None):
        tz = pytz.timezone(TZ_REGION)
        now = now or datetime.now(tz)
        return now.weekday() < 5 and OFFICE_START <= now.hour < OFFICE_END

    def after_hours_suffix(self, lang="EN"):
        return (
            "\n\nPS: Sekarang di luar waktu pejabat."
            if lang == "BM"
            else "\n\nPS: We’re currently outside office hours. A live agent will follow up later."
        )

    def add_footer(self, conversation_id, answer: str, lang: str, *, suppress: bool = False) -> str:
        # Higher turn threshold (was 7) so the LA footer only appears when the user
        # has clearly stuck around for a while. Callers can also pass `suppress=True`
        # for turns where the bot already gave a grounded answer (FAQ canonical /
        # tool-backed direct answer) so the footer does not nag every reply.
        footer = ""
        if not suppress and len(get_history(conversation_id)) >= 10:
            footer = FOOTER_BM if lang == "BM" else FOOTER_EN
        body = strip_bold_markdown_wrapping_around_urls((answer or "").rstrip())
        return body + footer

    def detect_car_support_query(self, text: str) -> bool:
        return any(k in text.lower() for k in CAR_KEYWORDS)

    def official_support_evidence(self, text: str) -> str:
        return _extract_support_evidence(text, _official_support_text())

    def extract_year(self, text: str) -> int | None:
        m = re.search(r"\b(19|20)\d{2}\b", text)
        return int(m.group()) if m else None

    def parse_year_range(self, text: str):
        match = re.search(r"(\d{4})[–-](\d{4})", text)
        if match:
            return int(match.group(1)), int(match.group(2))
        return None, None

    def run_rag_dual(self, user_text: str, lang_hint: str = "EN", user_id: str | None = None) -> str:
        sys_prompt = build_rag_system_prompt(dropoff_token=DROPOFF, testdrive_token=TESTDRIVE)
        lang_instruction = "Jawab dalam BM dengan nada mesra." if lang_hint == "BM" else "Answer politely in English."
        history_text = ""
        summary_text = ""
        facts_text = ""
        if user_id:
            history = get_history(user_id)
            if history:
                limited = history[-MEMORY_DEPTH:]
                history_text = "\n".join([f"{h['role']}: {h['text']}" for h in limited])
            summary_text = get_session_summary(user_id)
            facts = get_memory_facts(user_id)
            if facts:
                fact_lines = [f"- {f['fact_type']}:{f['fact_key']}={f['fact_value']}" for f in facts[:20]]
                facts_text = "\n".join(fact_lines)

        context = self.rag_sop.build_context(user_text, topk=4) if self.rag_sop else ""
        if context.strip():
            prompt = (
                f"Session summary:\n{summary_text}\n\n"
                f"Long-term facts:\n{facts_text}\n\n"
                f"Recent turns:\n{history_text}\n\n"
                f"User: {user_text}\n\nContext:\n{context}\n\n{lang_instruction}"
            )
            llm = chat_completion(sys_prompt, prompt)
            if llm:
                try:
                    if lang_hint == "BM":
                        llm = GoogleTranslator(source="auto", target="ms").translate(llm)
                except Exception as exc:  # noqa: BLE001
                    log.warning("[Translate] BM translation failed: %s", exc)
                return llm.strip()
        return ""

    def load_rag(self):
        try:
            self.rag_sop = RAGEngine(k=4, base_dir=os.path.join(RAG_DIR, "faiss_index"))
            log.info("[Kai] SOP RAG loaded")
        except Exception as exc:  # noqa: BLE001
            log.info("[Kai] SOP RAG not available: %s", exc)
            self.rag_sop = None

    def refresh_sop_and_warranty(self):
        try:
            qas = ingest_sop_qas()
            if qas:
                rebuild_rag()
                self.load_rag()
                log.info("Loaded %s SOP QAs", len(qas))
            else:
                log.warning("No SOP QAs from master_faq / doc / fallback")
            fetch_warranty_all()
            return {"ok": True, "qas_count": len(qas) if qas else 0}
        except Exception as exc:  # noqa: BLE001
            log.exception("Error refreshing SOP / warranty")
            return {"ok": False, "error": str(exc)}

    def startup(self):
        log.info("[Kai] sessions.db initialized")
        self.refresh_sop_and_warranty()

    def auto_refresh(self):
        try:
            fetch_warranty_all()
            log.info("[AutoRefresh] Warranty refreshed")
        except Exception as exc:  # noqa: BLE001
            log.error("[AutoRefresh] %s", exc)

    def admin_reset_memory(self, user_id: str | None):
        reset_memory(user_id)
        log.info("[ADMIN] Memory reset for %s", user_id)
        return "Memory reset completed"

    def pre_router(self, data: dict) -> dict | None:
        """Handover, frozen/resume, and session priming. Returns an immediate response dict, or None to continue."""
        text = data.get("content", "").strip()
        if not text:
            return {"ok": True}

        conversation_id = data.get("phone_number", "unknown")
        log.info("[Kai] IN conv=%s type=text text=%s", conversation_id, text)

        lower = re.sub(r"\s+", " ", (text or "").lower()).strip()
        sess = get_session(conversation_id)
        lang = "BM" if is_malay(text) else "EN"
        set_lang(conversation_id, lang)
        aft = not self.is_office_hours()
        update_session_summary(conversation_id, "user", text)
        extract_and_store_facts(conversation_id, text, source="user")
        cw_id = extract_chatwoot_conversation_id(data) or None

        if text == DROPOFF and not sess.get("frozen") and not sess.get("handover"):
            add_message_to_history(conversation_id, "user", text)
            start_human_segment(conversation_id, cw_id)
            append_human_segment_turn(conversation_id, "user", text)
            sess["frozen"] = True
            save_session(conversation_id, sess)
            msg_out = (
                "Please provide the date and time for the dropoff. Our staff will assist you soon. Type *resume* to continue with the bot."
                if lang == "EN"
                else "Sila berikan tarikh dan masa untuk penghantaran. Ejen kami akan membantu anda sebentar lagi. Taip *resume* untuk teruskan."
            )
            if aft:
                msg_out += self.after_hours_suffix(lang)
            append_human_segment_turn(conversation_id, "assistant", msg_out)
            return {"type": "handover", "message": msg_out, "next_state": "human"}

        if text in LIVEAGENT and not sess.get("frozen") and not sess.get("handover"):
            add_message_to_history(conversation_id, "user", text)
            start_human_segment(conversation_id, cw_id)
            append_human_segment_turn(conversation_id, "user", text)
            sess["frozen"] = True
            save_session(conversation_id, sess)
            msg_out = (
                "A live agent will assist you soon. Type *resume* to continue with the bot."
                if lang == "EN"
                else "Ejen kami akan membantu anda. Taip *resume* untuk teruskan."
            )
            if aft:
                msg_out += self.after_hours_suffix(lang)
            append_human_segment_turn(conversation_id, "assistant", msg_out)
            return {"type": "handover", "message": msg_out, "next_state": "human"}

        if sess.get("frozen"):
            if lower in {"resume", "unfreeze", "sambung"}:
                add_message_to_history(conversation_id, "user", text)
                schedule_faq_learn_after_handback(conversation_id)
                freeze(conversation_id, False)
                msg_out = "Bot resumed. How can I help?" if lang == "EN" else "Bot disambung semula. Ada apa saya boleh bantu?"
                add_message_to_history(conversation_id, "assistant", msg_out)
                update_session_summary(conversation_id, "assistant", msg_out)
                return {"type": "reply", "message": msg_out, "next_state": "bot"}
            add_message_to_history(conversation_id, "user", text)
            append_human_segment_turn(conversation_id, "user", text)
            return {"type": "frozen", "message": "", "next_state": "human"}

        return None

    def main_conversation(self, data: dict) -> dict:
        """Warranty dongle, car/RAG, and general RAG. Caller must have already run pre_router (user message in history)."""
        text = data.get("content", "").strip()
        conversation_id = data.get("phone_number", "unknown")
        lang = "BM" if is_malay(text) else "EN"

        if 6 <= len(text) <= 20:
            row = warranty_lookup_by_dongle(text)
            if row:
                msg_out = (
                    f"Warranty status: {warranty_text_from_row(row)}"
                    if lang == "EN"
                    else f"Status waranti: {warranty_text_from_row(row)}"
                )
                update_session_summary(conversation_id, "bot", msg_out)
                extract_and_store_facts(conversation_id, msg_out, source="bot")
                return {"type": "reply", "message": self.add_footer(conversation_id, msg_out, lang), "next_state": "bot"}

        if self.detect_car_support_query(text):
            support_hit = self.official_support_evidence(text)
            if support_hit:
                msg_out = (
                    "Based on our official support list, your vehicle appears supported. "
                    f"Reference: {support_hit}\n\n"
                    "If you want, I can walk you through self-installation steps, or optional HQ support if you prefer on-site help."
                    if lang == "EN"
                    else "Berdasarkan senarai sokongan rasmi kami, kenderaan anda kelihatan disokong. "
                    f"Rujukan: {support_hit}\n\n"
                    "Jika anda mahu, saya boleh bimbing pemasangan sendiri, atau sokongan di HQ jika anda perlukan bantuan di tapak."
                )
                add_message_to_history(conversation_id, "bot", msg_out)
                update_session_summary(conversation_id, "bot", msg_out)
                extract_and_store_facts(conversation_id, msg_out, source="bot")
                return {"type": "reply", "message": self.add_footer(conversation_id, msg_out, lang), "next_state": "bot"}

            answer = self.run_rag_dual(text, lang_hint=lang, user_id=conversation_id)
            lower_ans = answer.lower() if answer else ""
            year_in_text = self.extract_year(text)
            sop_years = self.parse_year_range(answer)
            if any(k in lower_ans for k in CAR_KEYWORDS):
                if sop_years != (None, None) and year_in_text:
                    start, end = sop_years
                    if year_in_text < start or year_in_text > end:
                        msg_out = (
                            f"Sorry, the {year_in_text} model is not supported. KommuAssist supports {start}–{end} variants only."
                            if lang == "EN"
                            else f"Maaf, model tahun {year_in_text} tidak disokong. KommuAssist hanya menyokong varian {start}–{end} sahaja."
                        )
                        add_message_to_history(conversation_id, "bot", msg_out)
                        update_session_summary(conversation_id, "bot", msg_out)
                        extract_and_store_facts(conversation_id, msg_out, source="bot")
                        return {
                            "type": "reply",
                            "message": self.add_footer(conversation_id, msg_out, lang),
                            "next_state": "bot",
                        }
                add_message_to_history(conversation_id, "bot", answer)
                update_session_summary(conversation_id, "bot", answer)
                extract_and_store_facts(conversation_id, answer, source="bot")
                return {"type": "reply", "message": self.add_footer(conversation_id, answer, lang), "next_state": "bot"}
            msg_out = (
                "I'm not sure about that car. Does it have Adaptive Cruise Control (ACC) and Lane Keep Assist (LKA)?"
                if lang == "EN"
                else "Saya tidak pasti tentang kereta itu. Adakah ia mempunyai sistem Adaptive Cruise Control (ACC) dan Lane Keep Assist (LKA)?"
            )
            set_last_intent(conversation_id, "car_unknown")
            add_message_to_history(conversation_id, "bot", msg_out)
            update_session_summary(conversation_id, "bot", msg_out)
            extract_and_store_facts(conversation_id, msg_out, source="bot")
            return {"type": "reply", "message": self.add_footer(conversation_id, msg_out, lang), "next_state": "bot"}

        answer = self.run_rag_dual(text, lang_hint=lang, user_id=conversation_id)
        if answer:
            add_message_to_history(conversation_id, "bot", answer)
            update_session_summary(conversation_id, "bot", answer)
            extract_and_store_facts(conversation_id, answer, source="bot")
            return {"type": "reply", "message": self.add_footer(conversation_id, answer, lang), "next_state": "bot"}
        return {"type": "reply", "message": "Retry please", "next_state": "bot"}

    def handle_agent_message(self, data: dict):
        if not data:
            raise ValueError("Invalid n8n payload")

        text = data.get("content", "").strip()
        if not text:
            return {"ok": True}

        early = self.pre_router(data)
        if early is not None:
            return early
        return self.main_conversation(data)

