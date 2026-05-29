from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Protocol

from openai import OpenAI

from kai.settings import get_settings

log = logging.getLogger("kai.providers")


class ChatProvider(Protocol):
    def chat(self, system_prompt: str, user_prompt: str, *, temperature: float = 0.2, max_tokens: int = 500) -> str:
        ...

    def chat_messages(self, messages: list[dict], *, temperature: float = 0.2, max_tokens: int = 1200) -> str:
        ...

    def embed(self, texts: list[str]) -> list[list[float]]:
        ...

    def rerank(self, query: str, docs: list[str]) -> list[float]:
        ...


@dataclass
class ProviderConfig:
    provider: str
    model: str
    base_url: str
    api_key: str
    embedding_model: str = ""


class DeepSeekProvider:
    _missing_key_warned = False

    def __init__(self, cfg: ProviderConfig) -> None:
        self.cfg = cfg
        self.client = OpenAI(api_key=cfg.api_key, base_url=cfg.base_url)

    def chat(self, system_prompt: str, user_prompt: str, *, temperature: float = 0.2, max_tokens: int = 500) -> str:
        return self.chat_messages(
            [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def chat_messages(self, messages: list[dict], *, temperature: float = 0.2, max_tokens: int = 1200) -> str:
        if not self.cfg.api_key:
            if not DeepSeekProvider._missing_key_warned:
                log.error(
                    "LLM call skipped: no API key configured. "
                    "Set KAI_LLM_API_KEY or DEEPSEEK_API_KEY (empty values shadow the alias). "
                    "Replies will fall back to clarify text until this is fixed."
                )
                DeepSeekProvider._missing_key_warned = True
            return ""
        resp = self.client.chat.completions.create(
            model=self.cfg.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        try:
            from kai.lib.llm_usage_record import record_openai_usage

            record_openai_usage(
                model=self.cfg.model,
                usage=getattr(resp, "usage", None),
                source="engine_chat",
            )
        except Exception:
            pass
        return (resp.choices[0].message.content or "").strip()

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self.cfg.api_key:
            try:
                model = self.cfg.embedding_model or get_settings().kai_embed_model
                resp = self.client.embeddings.create(model=model, input=texts)
                vecs = [list(d.embedding) for d in resp.data]
                if vecs:
                    return vecs
            except Exception:
                pass
        return [_cheap_embed(t) for t in texts]

    def rerank(self, query: str, docs: list[str]) -> list[float]:
        q = query.lower()
        return [min(1.0, 0.2 + _overlap_score(q, d.lower())) for d in docs]


class OpenAICompatibleProvider:
    """Generic OpenAI-compatible provider for non-DeepSeek backends."""

    _missing_key_warned = False

    def __init__(self, cfg: ProviderConfig) -> None:
        self.cfg = cfg
        self.client = OpenAI(api_key=cfg.api_key, base_url=cfg.base_url or None)

    def chat(self, system_prompt: str, user_prompt: str, *, temperature: float = 0.2, max_tokens: int = 500) -> str:
        return self.chat_messages(
            [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def chat_messages(self, messages: list[dict], *, temperature: float = 0.2, max_tokens: int = 1200) -> str:
        if not self.cfg.api_key:
            if not OpenAICompatibleProvider._missing_key_warned:
                log.error(
                    "LLM call skipped: no API key configured. "
                    "Set KAI_LLM_API_KEY (empty value shadows the alias). "
                    "Replies will fall back to clarify text until this is fixed."
                )
                OpenAICompatibleProvider._missing_key_warned = True
            return ""
        resp = self.client.chat.completions.create(
            model=self.cfg.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        try:
            from kai.lib.llm_usage_record import record_openai_usage

            record_openai_usage(
                model=self.cfg.model,
                usage=getattr(resp, "usage", None),
                source="engine_chat",
            )
        except Exception:
            pass
        return (resp.choices[0].message.content or "").strip()

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self.cfg.api_key:
            try:
                model = self.cfg.embedding_model or get_settings().kai_embed_model
                resp = self.client.embeddings.create(model=model, input=texts)
                vecs = [list(d.embedding) for d in resp.data]
                if vecs:
                    return vecs
            except Exception:
                pass
        return [_cheap_embed(t) for t in texts]

    def rerank(self, query: str, docs: list[str]) -> list[float]:
        q = query.lower()
        return [min(1.0, 0.2 + _overlap_score(q, d.lower())) for d in docs]


def _terms(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", (text or "").lower()) if t}


def _overlap_score(a: str, b: str) -> float:
    ta = _terms(a)
    tb = _terms(b)
    if not ta:
        return 0.0
    return len(ta.intersection(tb)) / max(1, len(ta))


def _cheap_embed(text: str, dims: int = 32) -> list[float]:
    vec = [0.0] * dims
    for idx, token in enumerate(sorted(_terms(text))):
        vec[idx % dims] += (sum(ord(c) for c in token) % 97) / 97.0
    norm = sum(v * v for v in vec) ** 0.5 or 1.0
    return [v / norm for v in vec]


def build_provider() -> ChatProvider:
    s = get_settings()
    provider_name = s.kai_llm_provider.strip().lower()
    if provider_name == "deepseek":
        cfg = ProviderConfig(
            provider="deepseek",
            model=s.kai_llm_model,
            base_url=s.kai_llm_base_url,
            api_key=s.kai_llm_api_key,
            embedding_model=s.kai_embed_model,
        )
        return DeepSeekProvider(cfg)

    cfg = ProviderConfig(
        provider=provider_name,
        model=s.kai_llm_model or "gpt-4o-mini",
        base_url=s.kai_llm_base_url,
        api_key=s.kai_llm_api_key,
        embedding_model=s.kai_embed_model,
    )
    return OpenAICompatibleProvider(cfg)
