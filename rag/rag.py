import os, pickle
import numpy as np
import faiss

FAISS_INDEX_FILE = "index.faiss"
META_FILE = "index.pkl"

def _l2_normalize(vec: np.ndarray) -> np.ndarray:
    if vec.ndim == 1:
        n = np.linalg.norm(vec)
        return vec if n == 0 else vec / n
    n = np.linalg.norm(vec, axis=1, keepdims=True)
    n[n == 0] = 1.0
    return vec / n

class RAGEngine:
    def __init__(self, k=4, base_dir=None):
        self.k = k
        self.base_dir = base_dir or os.path.join(os.path.dirname(__file__), "faiss_index")
        meta_path = os.path.join(self.base_dir, META_FILE)
        index_path = os.path.join(self.base_dir, FAISS_INDEX_FILE)

        if not (os.path.exists(meta_path) and os.path.exists(index_path)):
            raise FileNotFoundError(f"Missing FAISS artifacts in {self.base_dir}")

        with open(meta_path, "rb") as f:
            meta = pickle.load(f)

        self.data = meta["data"]
        self.model_name = meta.get("model") or "intfloat/multilingual-e5-base"

        self.backend = None
        self.embedder = None
        try:
            from fastembed import TextEmbedding
            supported = set(TextEmbedding.list_supported_models())
            if self.model_name in supported:
                self.embedder = TextEmbedding(model_name=self.model_name)
                self.backend = "fastembed"
            else:
                raise ValueError("model_not_supported_by_fastembed")
        except Exception:
            from sentence_transformers import SentenceTransformer
            self.embedder = SentenceTransformer(self.model_name)
            self.backend = "st"

        self.index = faiss.read_index(index_path)

    def _embed(self, texts):
        if self.backend == "fastembed":
            out = []
            for emb in self.embedder.embed(texts, batch_size=64):
                out.append(np.array(emb, dtype=np.float32))
            return np.vstack(out)
        else:
            arr = self.embedder.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=False,
                show_progress_bar=False
            ).astype("float32")
            return arr

    def _embed_query(self, text: str) -> np.ndarray:
        emb = self._embed([text])
        emb = _l2_normalize(emb).astype("float32")
        return emb

    def search(self, query: str, topk: int = None):
        q = self._embed_query(query)
        k = topk or self.k
        D, I = self.index.search(q, k)
        results = []
        for score, idx in zip(D[0], I[0]):
            if idx < 0:
                continue
            item = self.data[idx]
            results.append({"score": float(score), **item})
        return results

    def build_context(self, query: str, topk: int = None) -> str:
        hits = self.search(query, topk=topk or self.k)
        blocks = []
        for h in hits:
            src = h.get("source", "SOP")
            blocks.append(
                f"[score={h['score']:.3f} source={src}] "
                f"Q: {h.get('question','')}\nA: {h.get('answer','')}"
            )
        return "\n\n---\n\n".join(blocks)
