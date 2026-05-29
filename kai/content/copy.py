from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from kai.settings import get_settings
from kai.workspace.manifest import load_workspace_data, load_workspace_manifest


@dataclass(frozen=True)
class ChatCopy:
    live_agent: tuple[str, ...]
    footer_en: str
    footer_bm: str
    footer_history_threshold: int
    after_hours_en: str
    after_hours_bm: str
    handover_live_agent_en: str
    handover_live_agent_bm: str
    resume_en: str
    resume_bm: str
    media_guard_en: str

    def footer(self, lang: str) -> str:
        return self.footer_bm if lang == "BM" else self.footer_en

    def after_hours_suffix(self, lang: str) -> str:
        return self.after_hours_bm if lang == "BM" else self.after_hours_en

    def is_live_agent_keyword(self, text: str) -> bool:
        return text.strip().upper() in {k.upper() for k in self.live_agent}


def _load_yaml() -> dict:
    inline = load_workspace_data().get("copy")
    if isinstance(inline, dict) and inline:
        return inline
    return {}


@lru_cache(maxsize=1)
def get_chat_copy() -> ChatCopy:
    raw = _load_yaml()
    kw = raw.get("keywords") or {}
    footer = raw.get("footer") or {}
    ah = raw.get("after_hours") or {}
    ho = raw.get("handover") or {}
    res = raw.get("resume") or {}
    media = raw.get("media_guard") or {}
    live = kw.get("live_agent")
    if live is None:
        live = []
    elif isinstance(live, str):
        live = [live]
    return ChatCopy(
        live_agent=tuple(str(x) for x in live),
        footer_en=str(footer.get("en") or ""),
        footer_bm=str(footer.get("bm") or ""),
        footer_history_threshold=int(footer.get("history_threshold", 10)),
        after_hours_en=str(ah.get("en", "\n\nPS: We’re currently outside office hours. A live agent will follow up later.")),
        after_hours_bm=str(ah.get("bm", "\n\nPS: Sekarang di luar waktu pejabat.")),
        handover_live_agent_en=str(
            ho.get(
                "live_agent_en",
                "A live agent will assist you soon. Type *resume* to continue with the AI support agent.",
            )
        ),
        handover_live_agent_bm=str(
            ho.get(
                "live_agent_bm",
                "Ejen kami akan membantu anda. Taip *resume* untuk teruskan.",
            )
        ),
        resume_en=str(res.get("en", "AI support agent resumed. How can I help?")),
        resume_bm=str(res.get("bm", "Bot disambung semula. Ada apa saya boleh bantu?")),
        media_guard_en=str(
            media.get(
                "en",
                "I am a front-line diagnostic AI and do not support image/video/audio analysis yet. "
                "Please describe the issue in text and tell me what car you are driving (brand/model/year).",
            )
        ),
    )


def reload_chat_copy() -> ChatCopy:
    get_chat_copy.cache_clear()
    load_workspace_data.cache_clear()
    return get_chat_copy()
