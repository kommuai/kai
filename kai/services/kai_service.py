"""Session gates, outbound formatting, and admin helpers for the WhatsApp chatbot."""

from __future__ import annotations

from datetime import datetime
import logging
import re

import pytz

from config import OFFICE_END, OFFICE_START, SESSION_IDLE_HOURS, TZ_REGION
from kai.lib.lang_detect import is_malay
from kai.lib.media_handler import init_media_log
from kai.lib.session_state import (
    add_message_to_history,
    append_human_segment_turn,
    auto_unfreeze_stale_handoff,
    ensure_active_session,
    extract_and_store_facts,
    freeze,
    get_history,
    get_session,
    init_db,
    reset_memory,
    save_session,
    set_lang,
    start_human_segment,
    update_session_summary,
)
from kai.services.chatwoot_handover import extract_chatwoot_conversation_id
from kai.support_runtime.background_review import schedule_faq_learn_after_handback

log = logging.getLogger("kai")

DROPOFF = "DROPOFF"
LIVEAGENT = ["LA"]
FOOTER_EN = "\n\nFor Live Agent, type LA"
FOOTER_BM = "\n\nJika anda mahu bercakap dengan ejen yang sedia ada, taip LA"


def strip_bold_markdown_wrapping_around_urls(text: str) -> str:
    """Remove **bold** wrapping only around http(s) URLs (LLM habit breaks tappable links in WhatsApp, etc.)."""
    if not text:
        return text
    return re.sub(r"\*\*(https?://[^\s*]+)\*\*", r"\1", text)


class KaiService:
    def __init__(self) -> None:
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
        footer = ""
        if not suppress and len(get_history(conversation_id)) >= 10:
            footer = FOOTER_BM if lang == "BM" else FOOTER_EN
        body = strip_bold_markdown_wrapping_around_urls((answer or "").rstrip())
        return body + footer

    def prepare_outbound_message(
        self, conversation_id, answer: str, lang: str, *, suppress: bool = False
    ) -> tuple[str, dict]:
        """Footer + WhatsApp-safe length (Twilio text.body ≤ 4096)."""
        from kai.core.outbound_delivery import prepare_outbound_reply

        body = self.add_footer(conversation_id, answer, lang, suppress=suppress)
        return prepare_outbound_reply(body, lang)

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
        ensure_active_session(conversation_id)
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
            if auto_unfreeze_stale_handoff(conversation_id):
                log.info("[Kai] auto-unfreeze after %sh handoff idle conv=%s", SESSION_IDLE_HOURS, conversation_id)
                schedule_faq_learn_after_handback(conversation_id)
                sess = get_session(conversation_id)
            elif lower in {"resume", "unfreeze", "sambung"}:
                add_message_to_history(conversation_id, "user", text)
                schedule_faq_learn_after_handback(conversation_id)
                freeze(conversation_id, False)
                msg_out = (
                    "Bot resumed. How can I help?"
                    if lang == "EN"
                    else "Bot disambung semula. Ada apa saya boleh bantu?"
                )
                add_message_to_history(conversation_id, "assistant", msg_out)
                update_session_summary(conversation_id, "assistant", msg_out)
                return {"type": "reply", "message": msg_out, "next_state": "bot"}
            else:
                add_message_to_history(conversation_id, "user", text)
                append_human_segment_turn(conversation_id, "user", text)
                return {"type": "frozen", "message": "", "next_state": "human"}

        return None
