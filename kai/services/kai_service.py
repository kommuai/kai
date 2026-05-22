"""Session gates, outbound formatting, and admin helpers for the WhatsApp chatbot."""

from __future__ import annotations

import logging
import re

from kai.content.channels import get_channel_config
from kai.content.copy import get_chat_copy
from kai.lib.lang_detect import is_malay
from kai.lib.media_handler import init_media_log
from kai.lib.session_state import (
    add_message_to_history,
    append_human_segment_turn,
    auto_unfreeze_stale_handoff,
    ensure_active_session,
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
from kai.services.turn_ingest import ingest_user_turn
from kai.settings import get_settings
from kai.support_runtime.background_review import schedule_faq_learn_after_handback

log = logging.getLogger("kai")


def strip_bold_markdown_wrapping_around_urls(text: str) -> str:
    """Remove **bold** wrapping only around http(s) URLs (LLM habit breaks tappable links in WhatsApp, etc.)."""
    if not text:
        return text
    return re.sub(r"\*\*(https?://[^\s*]+)\*\*", r"\1", text)


class KaiService:
    def __init__(self) -> None:
        init_db()
        init_media_log()
        self._copy = get_chat_copy()
        self._channels = get_channel_config()
        self._settings = get_settings()

    def is_office_hours(self, now=None):
        return self._channels.is_office_hours(now)

    def after_hours_suffix(self, lang="EN"):
        return self._copy.after_hours_suffix(lang)

    def add_footer(self, conversation_id, answer: str, lang: str, *, suppress: bool = False) -> str:
        footer = ""
        from kai.workspace.runtime_settings import get_runtime_settings

        threshold = get_runtime_settings().footer_history_threshold
        if not suppress and len(get_history(conversation_id)) >= threshold:
            footer = self._copy.footer(lang)
        body = strip_bold_markdown_wrapping_around_urls((answer or "").rstrip())
        return body + footer

    def finalize_reply(self, conversation_id, answer: str, lang: str, *, suppress: bool = False) -> str:
        """Footer + WhatsApp-safe length (Twilio text.body ≤ 4096)."""
        from kai.core.outbound_delivery import prepare_outbound_reply

        body = self.add_footer(conversation_id, answer, lang, suppress=suppress)
        msg, _meta = prepare_outbound_reply(body, lang)
        return msg

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
        ingest_user_turn(conversation_id, text, record_history=False)
        cw_id = extract_chatwoot_conversation_id(data) or None
        cp = self._copy
        ch = self._channels

        if text == ch.dropoff_keyword and not sess.get("frozen") and not sess.get("handover"):
            add_message_to_history(conversation_id, "user", text)
            start_human_segment(conversation_id, cw_id)
            append_human_segment_turn(conversation_id, "user", text)
            sess["frozen"] = True
            save_session(conversation_id, sess)
            msg_out = cp.handover_dropoff_en if lang == "EN" else cp.handover_dropoff_bm
            if aft:
                msg_out += self.after_hours_suffix(lang)
            append_human_segment_turn(conversation_id, "assistant", msg_out)
            return {
                "type": "handover",
                "message": self.finalize_reply(conversation_id, msg_out, lang, suppress=True),
                "next_state": "human",
            }

        if ch.is_live_agent_keyword(text) and not sess.get("frozen") and not sess.get("handover"):
            add_message_to_history(conversation_id, "user", text)
            start_human_segment(conversation_id, cw_id)
            append_human_segment_turn(conversation_id, "user", text)
            sess["frozen"] = True
            save_session(conversation_id, sess)
            msg_out = cp.handover_live_agent_en if lang == "EN" else cp.handover_live_agent_bm
            if aft:
                msg_out += self.after_hours_suffix(lang)
            append_human_segment_turn(conversation_id, "assistant", msg_out)
            return {
                "type": "handover",
                "message": self.finalize_reply(conversation_id, msg_out, lang, suppress=True),
                "next_state": "human",
            }

        if sess.get("frozen"):
            idle_h = ch.frozen_idle_hours or self._settings.session_idle_hours
            if auto_unfreeze_stale_handoff(conversation_id, idle_hours=idle_h):
                log.info(
                    "[Kai] auto-unfreeze after %sh handoff idle conv=%s",
                    idle_h,
                    conversation_id,
                )
                schedule_faq_learn_after_handback(conversation_id)
                sess = get_session(conversation_id)
            elif ch.is_resume_keyword(text):
                add_message_to_history(conversation_id, "user", text)
                schedule_faq_learn_after_handback(conversation_id)
                freeze(conversation_id, False)
                msg_out = cp.resume_en if lang == "EN" else cp.resume_bm
                add_message_to_history(conversation_id, "assistant", msg_out)
                update_session_summary(conversation_id, "assistant", msg_out)
                return {
                    "type": "reply",
                    "message": self.finalize_reply(conversation_id, msg_out, lang, suppress=True),
                    "next_state": "bot",
                }
            else:
                add_message_to_history(conversation_id, "user", text)
                append_human_segment_turn(conversation_id, "user", text)
                return {"type": "frozen", "message": "", "next_state": "human"}

        return None
