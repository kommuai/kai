"""Vision / OCR providers for inbound images (Qwen-VL planned)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kai.media.config import get_media_config


@dataclass(frozen=True)
class VisionResult:
    extracted: str
    ocr_text: str
    caption: str
    confidence: float


def extract_image_text(path: Path, *, caption: str = "") -> VisionResult:
    """Extract text/description from an image. Requires vision.enabled in workspace."""
    cfg = get_media_config()
    if not cfg.vision_enabled:
        raise RuntimeError("vision_not_enabled")

    provider = (cfg.vision_provider or "").strip().lower()
    if provider in ("dashscope_qwen_vl", "qwen_vl", "qwen-vl"):
        raise NotImplementedError("qwen_vl_not_implemented")

    raise ValueError(f"unsupported_vision_provider:{provider}")
