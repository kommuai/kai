import os, json, pickle
import numpy as np, faiss
from fastembed import TextEmbedding
from config import SOP_JSON_PATH, FAISS_DIR

PREFERRED = [
    "intfloat/multilingual-e5-small",
    "intfloat/e5-small-v2",
    "intfloat/e5-base-v2",
    "intfloat/e5-small",
    "intfloat/e5-base",
]

def _normalize(v):
    n = np.linalg.norm(v)
    return v if n == 0 else (v / n)

def _supported_model_names():
    raw = TextEmbedding.list_supported_models()
    names = []
    for it in raw:
        if isinstance(it, str):
            names.append(it)
        elif isinstance(it, dict):
            for key in ("model", "name", "model_name", "id", "repo", "hf_repo"):
                val = it.get(key)
                if isinstance(val, str) and val:
                    names.append(val)
                    break
    # dedupe, preserve order
    seen, uniq = set(), []
    for n in names:
        if n not in seen:
            uniq.append(n); seen.add(n)
    return uniq

def _pick_model():
    names = _supported_model_names()
    if not names:
        raise RuntimeError("fastembed reports no supported models on this install.")
    for want in PREFERRED:
        if want in names:
            print(f"[fastembed] Using preferred model: {want}")
            return want
    print(f"[fastembed] Using fallback supported model: {names[0]}")
    return names[0]

def build():
    with open(SOP_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    os.makedirs(FAISS_DIR, exist_ok=True)
    model_name = _pick_model()
    embedder = TextEmbedding(model_name=model_name)

    corpus = [f"Q: {d['question']} A: {d['answer']}" for d in data]

    vecs = []
    for emb in embedder.embed(corpus, batch_size=64):
        vecs.append(_normalize(np.array(emb, dtype=np.float32)))
    embs = np.vstack(vecs)   # [N, D]
    dim = embs.shape[1]

    index = faiss.IndexFlatIP(dim)
    index.add(embs.astype(np.float32))

    with open(os.path.join(FAISS_DIR, "index.pkl"), "wb") as f:
        pickle.dump({"data": data, "model": model_name}, f)
    faiss.write_index(index, os.path.join(FAISS_DIR, "index.faiss"))
    print(f"Indexed {len(data)} entries → {FAISS_DIR}")

if __name__ == "__main__":
    build()
