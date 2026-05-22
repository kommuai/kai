from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from kai.workspace.manifest import load_workspace_manifest


@dataclass(frozen=True)
class ChannelConfig:
    office_timezone: str
    office_weekdays: tuple[int, ...]
    office_start_hour: int
    office_end_hour: int
    dropoff_keyword: str
    live_agent_keywords: tuple[str, ...]
    resume_keywords: tuple[str, ...]
    frozen_idle_hours: int | None
    blocked_media_types: tuple[str, ...]
    media_guard_en: str
    media_guard_bm: str
    clarify_no_signal_en: str
    clarify_no_signal_bm: str
    clarify_post_tool_en: str
    clarify_post_tool_bm: str
    install_condense_head_en: str
    install_condense_head_bm: str
    install_condense_tail_en: str
    install_condense_tail_bm: str
    whatsapp_shortened_tail_en: str
    whatsapp_shortened_tail_bm: str

    def is_office_hours(self, now=None) -> bool:
        from datetime import datetime

        import pytz

        tz = pytz.timezone(self.office_timezone)
        now = now or datetime.now(tz)
        return now.weekday() in self.office_weekdays and self.office_start_hour <= now.hour < self.office_end_hour

    def is_live_agent_keyword(self, text: str) -> bool:
        return text.strip().upper() in {k.upper() for k in self.live_agent_keywords}

    def is_resume_keyword(self, text: str) -> bool:
        lower = text.strip().lower()
        return lower in {k.lower() for k in self.resume_keywords}

    def is_blocked_media_type(self, msg_type: str) -> bool:
        return (msg_type or "").strip().lower() in {t.lower() for t in self.blocked_media_types}


def _channels_path() -> Path:
    manifest = load_workspace_manifest()
    return manifest.resolve(manifest.paths.channels_handover)


def _load_yaml() -> dict[str, Any]:
    path = _channels_path()
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


@lru_cache(maxsize=1)
def get_channel_config() -> ChannelConfig:
    raw = _load_yaml()
    from kai.content.copy import get_chat_copy
    from kai.workspace.runtime_settings import get_runtime_settings

    cp = get_chat_copy()
    rt = get_runtime_settings()
    manifest = load_workspace_manifest()

    office = raw.get("office") if isinstance(raw.get("office"), dict) else {}
    handover = raw.get("handover") if isinstance(raw.get("handover"), dict) else {}
    frozen = raw.get("frozen") if isinstance(raw.get("frozen"), dict) else {}
    media = raw.get("media") if isinstance(raw.get("media"), dict) else {}
    fallbacks = raw.get("fallbacks") if isinstance(raw.get("fallbacks"), dict) else {}

    weekdays = office.get("weekdays")
    if isinstance(weekdays, list) and weekdays:
        office_weekdays = tuple(int(x) for x in weekdays)
    else:
        office_weekdays = (0, 1, 2, 3, 4)

    live = handover.get("live_agent_keywords") or ["LA"]
    if isinstance(live, str):
        live = [live]
    resume = handover.get("resume_keywords") or ["resume", "unfreeze", "sambung"]
    if isinstance(resume, str):
        resume = [resume]

    blocked = media.get("blocked_types") or ["image", "video", "audio", "voice"]
    if isinstance(blocked, str):
        blocked = [blocked]

    return ChannelConfig(
        office_timezone=str(office.get("timezone") or manifest.timezone or rt.timezone),
        office_weekdays=office_weekdays,
        office_start_hour=int(office.get("start_hour") if office.get("start_hour") is not None else rt.office_start_hour),
        office_end_hour=int(office.get("end_hour") if office.get("end_hour") is not None else rt.office_end_hour),
        dropoff_keyword=str(handover.get("dropoff_keyword") or cp.dropoff),
        live_agent_keywords=tuple(str(x) for x in live),
        resume_keywords=tuple(str(x) for x in resume),
        frozen_idle_hours=int(frozen["idle_hours"]) if frozen.get("idle_hours") is not None else None,
        blocked_media_types=tuple(str(x) for x in blocked),
        media_guard_en=str(media.get("guard_en") or cp.media_guard_en),
        media_guard_bm=str(media.get("guard_bm") or media.get("guard_en") or cp.media_guard_en),
        clarify_no_signal_en=str(
            fallbacks.get("no_signal_en")
            or "What do you need help with? Tell me your question and I will look it up."
        ),
        clarify_no_signal_bm=str(
            fallbacks.get("no_signal_bm") or "Apa yang anda perlukan? Beritahu soalan anda."
        ),
        clarify_post_tool_en=str(
            fallbacks.get("post_tool_en")
            or "What is the exact detail I still need (model, year, ID, or error message)?"
        ),
        clarify_post_tool_bm=str(
            fallbacks.get("post_tool_bm") or "Apakah maklumat tepat yang masih diperlukan?"
        ),
        install_condense_head_en=str(fallbacks.get("install_head_en") or "Installation summary:"),
        install_condense_head_bm=str(fallbacks.get("install_head_bm") or "Ringkasan pemasangan:"),
        install_condense_tail_en=str(
            fallbacks.get("install_tail_en") or "Type your live-agent keyword if you need a full walkthrough."
        ),
        install_condense_tail_bm=str(
            fallbacks.get("install_tail_bm") or "Taip kata kunci ejen langsung jika anda perlukan panduan penuh."
        ),
        whatsapp_shortened_tail_en=str(
            fallbacks.get("whatsapp_short_en") or "\n\n(Message shortened for channel limit.)"
        ),
        whatsapp_shortened_tail_bm=str(
            fallbacks.get("whatsapp_short_bm") or "\n\n(Mesej dipendekkan untuk had saluran.)"
        ),
    )


def reload_channel_config() -> ChannelConfig:
    get_channel_config.cache_clear()
    return get_channel_config()
