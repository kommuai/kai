from __future__ import annotations

import json
import logging
from pathlib import Path
import re
from math import sqrt

from kai.settings import get_settings
from kai.support_runtime.models import RetrievalItem
from kai.support_runtime.providers import ChatProvider

try:
    from qdrant_client import QdrantClient
except Exception:  # noqa: BLE001
    QdrantClient = None

_log = logging.getLogger("kai.retrieval")


def _chunks_path() -> Path:
    return get_settings().kai_home / "compiled" / "kb_chunks.jsonl"


def _terms(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", (text or "").lower()) if t}


class HybridRetriever:
    """Qdrant hybrid retrieval with local fallback."""

    def __init__(self, provider: ChatProvider | None = None) -> None:
        self.items: list[dict] = []
        self.provider = provider
        s = get_settings()
        self.collection = s.kai_qdrant_collection
        self.use_qdrant = s.kai_qdrant_enabled
        self.client = None

    def load(self) -> None:
        self.items = []
        chunks_path = _chunks_path()
        if not chunks_path.exists():
            return
        for line in chunks_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                self.items.append(json.loads(line))
            except Exception:
                continue
        if self.use_qdrant and not QdrantClient:
            _log.warning(
                "KAI_QDRANT_ENABLED is set but qdrant-client is not installed; using local retrieval only"
            )
        if self.use_qdrant and QdrantClient:
            try:
                s = get_settings()
                self.client = QdrantClient(
                    url=s.kai_qdrant_url,
                    api_key=s.kai_qdrant_api_key or None,
                )
            except Exception:
                self.client = None

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        if not a or not b:
            return 0.0
        n = min(len(a), len(b))
        if n <= 0:
            return 0.0
        dot = sum(a[i] * b[i] for i in range(n))
        na = sqrt(sum(a[i] * a[i] for i in range(n))) or 1.0
        nb = sqrt(sum(b[i] * b[i] for i in range(n))) or 1.0
        return dot / (na * nb)

    def _retrieve_qdrant(self, query: str, top_k: int, metadata_filter: dict | None) -> list[RetrievalItem]:
        if not self.client or not self.provider:
            return []
        vector = self.provider.embed([query])[0]
        q_filter = None
        if metadata_filter:
            q_filter = {
                "must": [
                    {"key": k, "match": {"value": v}}
                    for k, v in metadata_filter.items()
                ]
            }
        try:
            hits = self.client.search(
                collection_name=self.collection,
                query_vector=vector,
                limit=top_k,
                query_filter=q_filter,
            )
            out = []
            for h in hits:
                payload = h.payload or {}
                out.append(
                    RetrievalItem(
                        source_id=payload.get("source_id", ""),
                        text=payload.get("text", ""),
                        score=float(getattr(h, "score", 0.0)),
                        metadata=payload.get("metadata", {}),
                    )
                )
            return out
        except Exception:
            return []

    def retrieve(self, query: str, *, top_k: int = 8, metadata_filter: dict | None = None) -> list[RetrievalItem]:
        if self.client:
            qdrant_items = self._retrieve_qdrant(query, top_k, metadata_filter)
            if qdrant_items:
                return qdrant_items
        q = _terms(query)
        query_vec: list[float] = []
        chunk_vecs: list[list[float]] = []
        if self.provider and self.items:
            try:
                texts = [query] + [str(i.get("text", "")) for i in self.items]
                all_vecs = self.provider.embed(texts)
                if all_vecs and len(all_vecs) == len(texts):
                    query_vec = all_vecs[0]
                    chunk_vecs = all_vecs[1:]
            except Exception:
                query_vec = []
                chunk_vecs = []
        out: list[RetrievalItem] = []
        for idx, item in enumerate(self.items):
            md = item.get("metadata", {})
            if metadata_filter and any(md.get(k) != v for k, v in metadata_filter.items()):
                continue
            txt = item.get("text", "")
            t = _terms(txt)
            overlap = len(q.intersection(t))
            dense_like = overlap / max(1, len(q))
            sparse_like = overlap / max(1, len(t))
            sem_like = 0.0
            if query_vec and idx < len(chunk_vecs):
                sem_like = max(0.0, self._cosine(query_vec, chunk_vecs[idx]))
            score = 0.5 * sem_like + 0.35 * dense_like + 0.15 * sparse_like
            try:
                dp = int(md.get("dynamic_priority") or 0)
            except (TypeError, ValueError):
                dp = 0
            if dp:
                score += min(0.45, 0.045 * dp)
            if score <= 0:
                continue
            out.append(
                RetrievalItem(
                    source_id=item.get("source_id", ""),
                    text=txt,
                    score=score,
                    metadata=md,
                )
            )
        return sorted(out, key=lambda x: x.score, reverse=True)[:top_k]


class SimpleReranker:
    """BGE/Jina/FlashRank-like API with provider-backed fallback scoring."""

    def __init__(self, provider: ChatProvider | None = None) -> None:
        self.provider = provider
        self.backend = get_settings().kai_reranker_backend.strip().lower()

    def rerank(self, query: str, items: list[RetrievalItem], *, top_k: int = 4) -> list[RetrievalItem]:
        if self.provider and items:
            docs = [i.text for i in items]
            model_scores = self.provider.rerank(query, docs)
        else:
            model_scores = [0.0] * len(items)
        q = _terms(query)
        rescored: list[RetrievalItem] = []
        for idx, item in enumerate(items):
            base = item.score
            bonus = 0.0
            meta = item.metadata or {}
            if "intent_id" in meta and any(tok in meta["intent_id"] for tok in q):
                bonus += 0.15
            if meta.get("category") == "known_faq_intent":
                bonus += 0.05
            if meta.get("category") == "dynamic_faq":
                bonus += 0.06
            try:
                dp = int(meta.get("dynamic_priority") or 0)
            except (TypeError, ValueError):
                dp = 0
            if dp:
                bonus += min(0.4, 0.04 * dp)
            bonus += min(0.3, model_scores[idx] if idx < len(model_scores) else 0.0)
            rescored.append(
                RetrievalItem(
                    source_id=item.source_id,
                    text=item.text,
                    score=min(1.0, base + bonus),
                    metadata=item.metadata,
                )
            )
        return sorted(rescored, key=lambda x: x.score, reverse=True)[:top_k]
