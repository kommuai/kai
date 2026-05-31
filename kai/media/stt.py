"""Speech-to-text providers for inbound voice/audio."""

from __future__ import annotations

import json
import math
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from kai.media.config import get_media_config


@dataclass(frozen=True)
class SttResult:
    transcript: str
    confidence: float
    language: str = ""


def _stt_server_url() -> str:
    return (os.getenv("KAI_STT_SERVER_URL") or "http://127.0.0.1:18792").rstrip("/")


def _stt_credentials() -> tuple[str, str, str]:
    api_key = (
        os.getenv("KAI_STT_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or ""
    ).strip()
    base_url = (os.getenv("KAI_STT_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
    cfg = get_media_config()
    model = (os.getenv("KAI_STT_MODEL") or cfg.stt_model or "whisper-1").strip()
    return api_key, base_url, model


def _confidence_from_segments(segments: list) -> float:
    if not segments:
        return 0.0
    logprobs = []
    for seg in segments:
        if isinstance(seg, dict):
            lp = seg.get("avg_logprob")
        else:
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


def _transcribe_via_server(path: Path) -> SttResult:
    url = f"{_stt_server_url()}/transcribe"
    payload = json.dumps({"path": str(path)}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"stt_server_unavailable:{exc}") from exc

    if not data.get("ok"):
        raise RuntimeError(str(data.get("error") or "stt_server_failed"))
    return SttResult(
        transcript=str(data.get("transcript") or "").strip(),
        confidence=float(data.get("confidence") or 0.0),
        language=str(data.get("language") or "").strip(),
    )


def _transcribe_openai_api(path: Path) -> SttResult:
    api_key, base_url, model = _stt_credentials()
    if not api_key:
        raise RuntimeError("stt_not_configured")

    from openai import OpenAI

    cfg = get_media_config()
    client = OpenAI(api_key=api_key, base_url=base_url)
    language_hint = cfg.stt_languages[0] if len(cfg.stt_languages) == 1 else None

    with path.open("rb") as audio_file:
        kwargs: dict = {
            "model": model,
            "file": audio_file,
            "response_format": "verbose_json",
        }
        if language_hint:
            kwargs["language"] = language_hint
        resp = client.audio.transcriptions.create(**kwargs)

    try:
        from kai.lib.llm_usage_record import record_openai_usage

        record_openai_usage(model=model, usage=None, source="media_stt")
    except Exception:
        pass

    text = (getattr(resp, "text", None) or "").strip()
    segments = getattr(resp, "segments", None) or []
    lang = (getattr(resp, "language", None) or "").strip()
    confidence = _confidence_from_segments(list(segments))
    if text and confidence <= 0.0:
        confidence = 0.85
    return SttResult(transcript=text, confidence=confidence, language=lang)


def transcribe_audio(path: Path) -> SttResult:
    """Transcribe audio file using configured STT provider."""
    cfg = get_media_config()
    provider = (cfg.stt_provider or "faster_whisper").strip().lower()

    if provider in ("faster_whisper", "local", "whisper_local"):
        if _server_health_ok():
            try:
                return _transcribe_via_server(path)
            except RuntimeError:
                pass
        from kai.media.stt_local import transcribe_local

        return transcribe_local(path)

    if provider in ("openai_whisper", "whisper", "openai"):
        return _transcribe_openai_api(path)

    raise ValueError(f"unsupported_stt_provider:{provider}")


def _server_health_ok() -> bool:
    url = f"{_stt_server_url()}/health"
    try:
        with urllib.request.urlopen(url, timeout=1.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return bool(data.get("ok"))
    except Exception:
        return False
