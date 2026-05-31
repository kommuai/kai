"""Normalize inbound media into text for run_support_turn."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kai.media.config import get_media_config
from kai.media.stt import transcribe_audio
from kai.media.storage import store_inbound_media
from kai.media.vision import extract_image_text


@dataclass(frozen=True)
class EnrichedTurn:
    text: str
    modality: str
    confidence: float = 1.0
    stored_path: str = ""
    skipped_runtime: bool = False
    decision: str = ""
    metadata: dict[str, Any] | None = None


def _apply_template(template: str, **kwargs: str) -> str:
    try:
        return template.format(**kwargs).strip()
    except KeyError:
        return template.strip()


def enrich_inbound_media(payload: dict[str, Any], *, lang: str) -> EnrichedTurn:
    """Convert inbound media payload to enriched user text."""
    modality = str(payload.get("modality") or "").strip().lower()
    cfg = get_media_config()
    caption = str(payload.get("caption") or "").strip()
    msg_id = str(payload.get("msg_id") or "").strip()
    mimetype = str(payload.get("mimetype") or "").strip()

    raw_path = str(payload.get("path") or "").strip()
    if not raw_path:
        raise ValueError("media_path_required")
    source = Path(raw_path)
    if not source.is_file():
        raise FileNotFoundError(f"media_source_missing:{raw_path}")

    stored = store_inbound_media(
        source_path=source,
        msg_id=msg_id,
        modality=modality,
        mimetype=mimetype,
    )

    if modality in ("voice", "audio"):
        if not cfg.stt_enabled:
            fallback = cfg.voice_fallback_en if lang == "EN" else cfg.voice_fallback_bm
            return EnrichedTurn(
                text=fallback,
                modality=modality,
                stored_path=str(stored),
                skipped_runtime=True,
                decision="media_guard",
            )

        try:
            stt = transcribe_audio(stored)
        except Exception as exc:
            fallback = cfg.voice_fallback_en if lang == "EN" else cfg.voice_fallback_bm
            return EnrichedTurn(
                text=fallback,
                modality=modality,
                stored_path=str(stored),
                skipped_runtime=True,
                decision="stt_failed",
                metadata={"error": str(exc)[:200]},
            )

        if not stt.transcript or stt.confidence < cfg.stt_min_confidence:
            fallback = cfg.voice_fallback_en if lang == "EN" else cfg.voice_fallback_bm
            return EnrichedTurn(
                text=fallback,
                modality=modality,
                confidence=stt.confidence,
                stored_path=str(stored),
                skipped_runtime=True,
                decision="stt_low_confidence",
                metadata={"transcript": stt.transcript, "language": stt.language},
            )

        template = cfg.voice_template_en if lang == "EN" else cfg.voice_template_bm
        parts = [_apply_template(template, transcript=stt.transcript)]
        if caption and caption.lower() not in stt.transcript.lower():
            parts.append(caption)
        text = "\n".join(p for p in parts if p).strip()
        return EnrichedTurn(
            text=text,
            modality=modality,
            confidence=stt.confidence,
            stored_path=str(stored),
            metadata={
                "transcript": stt.transcript,
                "language": stt.language,
                "source_modality": modality,
            },
        )

    if modality == "image":
        if not cfg.vision_enabled:
            raise ValueError("image_not_supported")

        vision = extract_image_text(stored, caption=caption)
        template = cfg.image_template_en if lang == "EN" else cfg.image_template_bm
        extracted = vision.extracted or vision.ocr_text or vision.caption
        if not extracted or vision.confidence < cfg.vision_min_confidence:
            fallback = cfg.image_fallback_en if lang == "EN" else cfg.image_fallback_bm
            return EnrichedTurn(
                text=fallback,
                modality=modality,
                confidence=vision.confidence,
                stored_path=str(stored),
                skipped_runtime=True,
                decision="vision_low_confidence",
            )
        text = _apply_template(template, extracted=extracted)
        if caption:
            text = f"{caption}\n{text}".strip()
        return EnrichedTurn(
            text=text,
            modality=modality,
            confidence=vision.confidence,
            stored_path=str(stored),
            metadata={"ocr_text": vision.ocr_text, "caption": vision.caption},
        )

    raise ValueError(f"unsupported_modality:{modality}")
