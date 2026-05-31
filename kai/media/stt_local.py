"""Local Whisper via faster-whisper (free, no API key)."""

from __future__ import annotations

import math
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from kai.media.config import get_media_config
from kai.media.stt import SttResult


def _device_and_compute() -> tuple[str, str]:
    device = (os.getenv("KAI_STT_DEVICE") or "auto").strip().lower()
    compute = (os.getenv("KAI_STT_COMPUTE_TYPE") or "").strip().lower()
    if device == "auto":
        device = "cuda" if _cuda_available() else "cpu"
    if not compute:
        compute = "float16" if device == "cuda" else "int8"
    return device, compute


def _cuda_available() -> bool:
    try:
        import ctranslate2

        return bool(ctranslate2.get_cuda_device_count())
    except Exception:
        return False


@lru_cache(maxsize=1)
def _load_model() -> Any:
    from faster_whisper import WhisperModel

    cfg = get_media_config()
    model_name = (os.getenv("KAI_STT_MODEL") or cfg.stt_model or "small").strip()
    device, compute_type = _device_and_compute()
    return WhisperModel(model_name, device=device, compute_type=compute_type)


def _confidence_from_segments(segments: list) -> float:
    logprobs = []
    for seg in segments:
        lp = getattr(seg, "avg_logprob", None)
        if lp is not None:
            try:
                logprobs.append(float(lp))
            except (TypeError, ValueError):
                continue
    if not logprobs:
        return 0.85
    avg = sum(logprobs) / len(logprobs)
    return max(0.0, min(1.0, math.exp(avg)))


def transcribe_local(path: Path) -> SttResult:
    cfg = get_media_config()
    model = _load_model()
    language = cfg.stt_languages[0] if len(cfg.stt_languages) == 1 else None
    kwargs: dict[str, Any] = {"vad_filter": True}
    if language:
        kwargs["language"] = language

    segment_iter, info = model.transcribe(str(path), **kwargs)
    segments = list(segment_iter)
    text = "".join(getattr(seg, "text", "") or "" for seg in segments).strip()
    lang = (getattr(info, "language", None) or "").strip()
    confidence = _confidence_from_segments(segments)
    if text and confidence <= 0.0:
        confidence = 0.85
    return SttResult(transcript=text, confidence=confidence, language=lang)
