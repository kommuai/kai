"""Inbound media configuration from workspace.yaml channels.media."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from kai.workspace.manifest import load_workspace_data


@dataclass(frozen=True)
class MediaConfig:
    blocked_types: tuple[str, ...]
    storage_dir: str
    max_bytes: int
    stt_enabled: bool
    stt_provider: str
    stt_model: str
    stt_min_confidence: float
    stt_languages: tuple[str, ...]
    vision_min_confidence: float
    voice_template_en: str
    voice_template_bm: str
    voice_fallback_en: str
    voice_fallback_bm: str
    vision_enabled: bool
    vision_provider: str
    vision_model: str
    image_template_en: str
    image_template_bm: str
    image_fallback_en: str
    image_fallback_bm: str

    def supports_inbound(self, modality: str) -> bool:
        t = (modality or "").strip().lower()
        if t in ("voice", "audio") and self.stt_enabled:
            return True
        if t == "image" and self.vision_enabled:
            return True
        return False

    def is_modality_blocked(self, modality: str) -> bool:
        t = (modality or "").strip().lower()
        if not t:
            return False
        if self.supports_inbound(t):
            return False
        blocked = {x.lower() for x in self.blocked_types}
        aliases = {"voice": "audio", "audio": "voice"}
        if t in blocked:
            return True
        alt = aliases.get(t)
        return bool(alt and alt in blocked)


def _media_yaml() -> dict[str, Any]:
    data = load_workspace_data()
    channels = data.get("channels") if isinstance(data.get("channels"), dict) else {}
    media = channels.get("media") if isinstance(channels.get("media"), dict) else {}
    return media


@lru_cache(maxsize=1)
def get_media_config() -> MediaConfig:
    media = _media_yaml()
    blocked = media.get("blocked_types") or ["image", "video", "audio", "voice"]
    if isinstance(blocked, str):
        blocked = [blocked]

    stt = media.get("stt") if isinstance(media.get("stt"), dict) else {}
    vision = media.get("vision") if isinstance(media.get("vision"), dict) else {}
    enrich = media.get("enrich") if isinstance(media.get("enrich"), dict) else {}

    langs = stt.get("languages") or ["en", "ms"]
    if isinstance(langs, str):
        langs = [langs]

    return MediaConfig(
        blocked_types=tuple(str(x) for x in blocked),
        storage_dir=str(media.get("storage_dir") or "data/media"),
        max_bytes=int(media.get("max_bytes") or 10_485_760),
        stt_enabled=bool(stt.get("enabled", True)),
        stt_provider=str(stt.get("provider") or "faster_whisper"),
        stt_model=str(stt.get("model") or "small"),
        stt_min_confidence=float(stt.get("min_confidence") if stt.get("min_confidence") is not None else 0.5),
        stt_languages=tuple(str(x) for x in langs),
        vision_min_confidence=float(
            vision.get("min_confidence") if vision.get("min_confidence") is not None else 0.7
        ),
        voice_template_en=str(
            enrich.get("voice_template_en") or "[Voice message]: {transcript}"
        ),
        voice_template_bm=str(
            enrich.get("voice_template_bm") or "[Mesej suara]: {transcript}"
        ),
        voice_fallback_en=str(
            enrich.get("voice_fallback_en")
            or "I couldn't make out your voice message. Please type your question."
        ),
        voice_fallback_bm=str(
            enrich.get("voice_fallback_bm")
            or "Saya tidak dapat dengar mesej suara anda. Sila taip soalan anda."
        ),
        vision_enabled=bool(vision.get("enabled", False)),
        vision_provider=str(vision.get("provider") or "dashscope_qwen_vl"),
        vision_model=str(vision.get("model") or "qwen-vl-max"),
        image_template_en=str(
            enrich.get("image_template_en") or "[Image]: {extracted}"
        ),
        image_template_bm=str(
            enrich.get("image_template_bm") or "[Imej]: {extracted}"
        ),
        image_fallback_en=str(
            enrich.get("image_fallback_en")
            or "I couldn't read that image clearly. Please describe the issue in text."
        ),
        image_fallback_bm=str(
            enrich.get("image_fallback_bm")
            or "Saya tidak dapat baca imej itu dengan jelas. Sila terangkan isu anda."
        ),
    )


def reload_media_config() -> MediaConfig:
    get_media_config.cache_clear()
    load_workspace_data.cache_clear()
    return get_media_config()
