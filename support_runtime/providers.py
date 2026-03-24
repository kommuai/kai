from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Protocol
import re

from openai import OpenAI

from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL


class ChatProvider(Protocol):
    def chat(self, system_prompt: str, user_prompt: str, *, temperature: float = 0.2, max_tokens: int = 500) -> str:
        ...

    def chat_messages(self, messages: list[dict], *, temperature: float = 0.2, max_tokens: int = 1200) -> str:
        ...

    def embed(self, texts: list[str]) -> list[list[float]]:
        ...

    def classify(self, text: str, labels: list[str]) -> tuple[str, float]:
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
            return ""
        resp = self.client.chat.completions.create(
            model=self.cfg.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return (resp.choices[0].message.content or "").strip()

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self.cfg.api_key:
            try:
                model = self.cfg.embedding_model or os.getenv("KAI_EMBED_MODEL", "text-embedding-3-small")
                resp = self.client.embeddings.create(model=model, input=texts)
                vecs = [list(d.embedding) for d in resp.data]
                if vecs:
                    return vecs
            except Exception:
                pass
        return [_cheap_embed(t) for t in texts]

    def classify(self, text: str, labels: list[str]) -> tuple[str, float]:
        if self.cfg.api_key and labels:
            try:
                prompt = (
                    "Choose the single best label for the message.\n"
                    f"Labels: {', '.join(labels)}\n"
                    "Return only JSON: {\"label\":\"...\",\"confidence\":0.0-1.0}\n"
                    f"Message: {text}"
                )
                resp = self.client.chat.completions.create(
                    model=self.cfg.model,
                    messages=[
                        {"role": "system", "content": "You are a strict intent classifier."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.0,
                    max_tokens=120,
                )
                raw = (resp.choices[0].message.content or "").strip()
                m = re.search(r"\{.*\}", raw, flags=re.S)
                if m:
                    parsed = __import__("json").loads(m.group(0))
                    label = str(parsed.get("label", "")).strip()
                    conf = float(parsed.get("confidence", 0.0))
                    if label in labels:
                        return label, max(0.0, min(1.0, conf))
            except Exception:
                pass
        t = text.lower()
        best = labels[0] if labels else "unknown"
        best_score = 0.0
        for label in labels:
            score = _overlap_score(t, label.lower())
            if score > best_score:
                best, best_score = label, score
        return best, min(0.99, 0.5 + best_score)

    def rerank(self, query: str, docs: list[str]) -> list[float]:
        q = query.lower()
        return [min(1.0, 0.2 + _overlap_score(q, d.lower())) for d in docs]


class OpenAICompatibleProvider:
    """Generic OpenAI-compatible provider for non-DeepSeek backends."""

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
            return ""
        resp = self.client.chat.completions.create(
            model=self.cfg.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return (resp.choices[0].message.content or "").strip()

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self.cfg.api_key:
            try:
                model = self.cfg.embedding_model or os.getenv("KAI_EMBED_MODEL", "text-embedding-3-small")
                resp = self.client.embeddings.create(model=model, input=texts)
                vecs = [list(d.embedding) for d in resp.data]
                if vecs:
                    return vecs
            except Exception:
                pass
        return [_cheap_embed(t) for t in texts]

    def classify(self, text: str, labels: list[str]) -> tuple[str, float]:
        if self.cfg.api_key and labels:
            try:
                prompt = (
                    "Choose the single best label for the message.\n"
                    f"Labels: {', '.join(labels)}\n"
                    "Return only JSON: {\"label\":\"...\",\"confidence\":0.0-1.0}\n"
                    f"Message: {text}"
                )
                resp = self.client.chat.completions.create(
                    model=self.cfg.model,
                    messages=[
                        {"role": "system", "content": "You are a strict intent classifier."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.0,
                    max_tokens=120,
                )
                raw = (resp.choices[0].message.content or "").strip()
                m = re.search(r"\{.*\}", raw, flags=re.S)
                if m:
                    parsed = __import__("json").loads(m.group(0))
                    label = str(parsed.get("label", "")).strip()
                    conf = float(parsed.get("confidence", 0.0))
                    if label in labels:
                        return label, max(0.0, min(1.0, conf))
            except Exception:
                pass
        t = text.lower()
        best = labels[0] if labels else "unknown"
        best_score = 0.0
        for label in labels:
            score = _overlap_score(t, label.lower())
            if score > best_score:
                best, best_score = label, score
        return best, min(0.99, 0.5 + best_score)

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
    provider_name = os.getenv("KAI_LLM_PROVIDER", "deepseek").strip().lower()
    if provider_name == "deepseek":
        cfg = ProviderConfig(
            provider="deepseek",
            model=os.getenv("KAI_LLM_MODEL", DEEPSEEK_MODEL),
            base_url=os.getenv("KAI_LLM_BASE_URL", DEEPSEEK_BASE_URL),
            api_key=os.getenv("KAI_LLM_API_KEY", DEEPSEEK_API_KEY),
            embedding_model=os.getenv("KAI_EMBED_MODEL", "text-embedding-3-small"),
        )
        return DeepSeekProvider(cfg)

    cfg = ProviderConfig(
        provider=provider_name,
        model=os.getenv("KAI_LLM_MODEL", "gpt-4o-mini"),
        base_url=os.getenv("KAI_LLM_BASE_URL", ""),
        api_key=os.getenv("KAI_LLM_API_KEY", ""),
        embedding_model=os.getenv("KAI_EMBED_MODEL", "text-embedding-3-small"),
    )
    return OpenAICompatibleProvider(cfg)
