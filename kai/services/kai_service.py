"""Session gates, outbound formatting, and admin helpers for the WhatsApp chatbot."""

from __future__ import annotations

import logging
import re

from kai.content.channels import get_channel_config, reload_channel_config
from kai.content.copy import get_chat_copy, reload_chat_copy
from kai.lib.lang import resolve_lang
from kai.lib.media_handler import init_media_log
from kai.lib.session_state import (
    add_message_to_history,
    auto_unfreeze_stale_handoff,
    ensure_active_session,
    freeze,
    get_history,
    get_session,
    init_db,
    reset_memory,
    save_session,
    set_lang,
    update_session_summary,
)
from kai.services.turn_ingest import ingest_user_turn
from kai.settings import get_settings

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
        self._settings = get_settings()

    def is_office_hours(self, now=None):
        return self._channels().is_office_hours(now)

    def _copy(self):
        return get_chat_copy()

    def _channels(self):
        return get_channel_config()

    def after_hours_suffix(self, lang="EN"):
        return self._copy().after_hours_suffix(lang)

    def add_footer(self, conversation_id, answer: str, lang: str, *, suppress: bool = False) -> str:
        footer = ""
        from kai.workspace.runtime_settings import get_runtime_settings

        threshold = get_runtime_settings().footer_history_threshold
        if not suppress and len(get_history(conversation_id)) >= threshold:
            footer = self._copy().footer(lang)
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

    def _admin_reply(self, conversation_id: str, msg: str, lang: str) -> dict:
        return {
            "type": "reply",
            "message": self.finalize_reply(conversation_id, msg, lang, suppress=True),
            "next_state": "bot",
        }

    def _handle_admin_commands(
        self,
        conversation_id: str,
        text: str,
        lower: str,
        sess: dict,
        lang: str,
    ) -> dict | None:
        """Handle /admin, /test, and /learning commands for whitelisted numbers.

        Returns a response dict to short-circuit, or None to continue normal routing.
        """
        from kai.workspace.admin_config import get_admin_config

        admin_cfg = get_admin_config()
        if not admin_cfg.is_admin(conversation_id):
            return None

        # --- /admin command ---
        if lower == "/admin":
            sess["admin_mode"] = True
            sess.pop("learning_state", None)
            save_session(conversation_id, sess)
            freeze(conversation_id, True)
            log.info("[Admin] admin_mode ON conv=%s", conversation_id)
            return self._admin_reply(
                conversation_id,
                "Admin mode on. AI support agent is paused for this number.\n"
                "Send /learning to review low-confidence questions, /test to switch to user mode.",
                lang,
            )

        # --- /test command ---
        if lower == "/test":
            sess["admin_mode"] = False
            sess.pop("learning_state", None)
            save_session(conversation_id, sess)
            freeze(conversation_id, False)
            log.info("[Admin] test_mode ON conv=%s", conversation_id)
            return self._admin_reply(
                conversation_id,
                "Test mode on. AI support agent will respond normally.",
                lang,
            )

        # --- /learning command (and sub-commands) ---
        if lower.startswith("/learning"):
            return self._handle_learning_command(conversation_id, lower, sess, lang, admin_cfg)

        # --- plain text while admin_mode is active (session is frozen — let normal frozen path handle it) ---
        return None

    def _handle_learning_command(
        self,
        conversation_id: str,
        lower: str,
        sess: dict,
        lang: str,
        admin_cfg,
    ) -> dict:
        from kai.lib.learning_events import fetch_pending_events, set_event_status

        if not sess.get("admin_mode"):
            return self._admin_reply(
                conversation_id,
                "Send /admin first to enter admin mode before using /learning.",
                lang,
            )

        learning_state = sess.get("learning_state") or {}

        # Active session sub-commands
        if learning_state:
            if lower in ("/learning skip", "/learning s"):
                current_id = learning_state.get("current_event_id")
                if current_id:
                    set_event_status(current_id, "skipped")
                return self._learning_advance(conversation_id, sess, learning_state, lang)

            if lower in ("/learning stop", "/learning x"):
                sess.pop("learning_state", None)
                save_session(conversation_id, sess)
                return self._admin_reply(conversation_id, "Learning session ended.", lang)

        # Start or restart /learning
        if lower == "/learning":
            events = fetch_pending_events(admin_cfg.learning.max_items)
            if not events:
                return self._admin_reply(
                    conversation_id,
                    "No new low-confidence questions to review.",
                    lang,
                )
            event_ids = [e["event_id"] for e in events]
            sess["learning_state"] = {
                "event_ids": event_ids,
                "index": 0,
                "current_event_id": event_ids[0],
            }
            save_session(conversation_id, sess)
            return self._learning_present(conversation_id, events[0], 1, len(event_ids), lang)

        # Fall through: unknown /learning sub-command
        return self._admin_reply(
            conversation_id,
            "Unknown command. Use /learning, /learning skip, or /learning stop.",
            lang,
        )

    def _learning_present(
        self,
        conversation_id: str,
        event: dict,
        num: int,
        total: int,
        lang: str,
    ) -> dict:
        msg = (
            f"Question {num} of {total}:\n"
            f"{event['user_text']}\n\n"
            "Type the correct answer, /learning skip to skip, or /learning stop to end."
        )
        return self._admin_reply(conversation_id, msg, lang)

    def _learning_advance(
        self,
        conversation_id: str,
        sess: dict,
        learning_state: dict,
        lang: str,
    ) -> dict:
        from kai.lib.learning_events import fetch_pending_events

        event_ids: list[str] = learning_state.get("event_ids", [])
        index: int = learning_state.get("index", 0) + 1

        if index >= len(event_ids):
            sess.pop("learning_state", None)
            save_session(conversation_id, sess)
            return self._admin_reply(
                conversation_id,
                f"All done. {len(event_ids)} question(s) reviewed. Run merge_learn_queue.py to apply saved proposals.",
                lang,
            )

        next_id = event_ids[index]
        sess["learning_state"] = {
            "event_ids": event_ids,
            "index": index,
            "current_event_id": next_id,
        }
        save_session(conversation_id, sess)

        # Fetch the event details for presentation
        remaining = fetch_pending_events(limit=len(event_ids) - index + 50)
        event = next((e for e in remaining if e["event_id"] == next_id), None)
        if not event:
            # Event already resolved or missing; skip to next
            return self._learning_advance(conversation_id, sess, sess["learning_state"], lang)

        return self._learning_present(conversation_id, event, index + 1, len(event_ids), lang)

    def _handle_admin_answer(
        self,
        conversation_id: str,
        text: str,
        sess: dict,
        lang: str,
    ) -> dict | None:
        """If admin is in an active learning session and sends plain text, treat it as an answer."""
        from kai.workspace.admin_config import get_admin_config

        admin_cfg = get_admin_config()
        if not admin_cfg.is_admin(conversation_id):
            return None
        if not sess.get("admin_mode"):
            return None
        learning_state = sess.get("learning_state") or {}
        if not learning_state:
            return None

        current_event_id = learning_state.get("current_event_id")
        if not current_event_id:
            return None

        # Generate proposal and advance
        try:
            from kai.lib.learning_events import fetch_pending_events, set_event_status
            from kai.support_runtime.admin_learn import generate_learning_proposal

            events = fetch_pending_events(limit=200)
            event = next((e for e in events if e["event_id"] == current_event_id), None)
            if event:
                generate_learning_proposal(
                    user_question=event["user_text"],
                    admin_answer=text,
                    event_meta=event,
                )
            set_event_status(current_event_id, "resolved")
        except Exception as exc:
            log.warning("[Admin] proposal generation failed: %s", exc)

        return self._learning_advance(conversation_id, sess, learning_state, lang)

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
        lang = resolve_lang(user_id=conversation_id)
        aft = not self.is_office_hours()
        ingest_user_turn(conversation_id, text, record_history=False)
        reload_chat_copy()
        reload_channel_config()
        cp = self._copy()
        ch = self._channels()

        # Admin commands are intercepted first (before any handover / frozen logic).
        admin_resp = self._handle_admin_commands(conversation_id, text, lower, sess, lang)
        if admin_resp is not None:
            return admin_resp

        # Admin in active learning session: plain text is an answer.
        admin_answer_resp = self._handle_admin_answer(conversation_id, text, sess, lang)
        if admin_answer_resp is not None:
            return admin_answer_resp

        if ch.is_live_agent_keyword(text) and not sess.get("frozen") and not sess.get("handover"):
            add_message_to_history(conversation_id, "user", text)
            freeze(conversation_id, True)
            msg_out = cp.handover_live_agent_en if lang == "EN" else cp.handover_live_agent_bm
            if aft:
                msg_out += self.after_hours_suffix(lang)
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
                sess = get_session(conversation_id)
            elif ch.is_resume_keyword(text):
                add_message_to_history(conversation_id, "user", text)
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
                return {"type": "frozen", "message": "", "next_state": "human"}

        return None
