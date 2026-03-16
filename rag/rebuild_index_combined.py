import os, json, pickle
import numpy as np, faiss
from sentence_transformers import SentenceTransformer
from config import FAISS_DIR, SOP_JSON_PATH

MODEL_NAME = "intfloat/multilingual-e5-base"

def _normalize(v):
    n = np.linalg.norm(v, axis=1, keepdims=True)
    n[n == 0] = 1.0
    return v / n

def rebuild():
    os.makedirs(FAISS_DIR, exist_ok=True)
    try:
        data = json.load(open(SOP_JSON_PATH, "r", encoding="utf-8"))
    except Exception as e:
        raise SystemExit(f"[ingest] Cannot read {SOP_JSON_PATH}: {e}")

    entries = [{"question": d["question"], "answer": d["answer"], "source": "SOP"}
               for d in data if d.get("question") and d.get("answer")]
    if not entries:
        raise SystemExit("[ingest] No SOP entries to index.")

    corpus = [f"Q: {e['question']}\nA: {e['answer']}" for e in entries]
    print(f"[ingest] Embedding {len(corpus)} entries with {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)
    embs = model.encode(corpus, convert_to_numpy=True, normalize_embeddings=False, show_progress_bar=False).astype("float32")
    embs = _normalize(embs)
    dim = embs.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embs)

    faiss.write_index(index, os.path.join(FAISS_DIR, "index.faiss"))
    with open(os.path.join(FAISS_DIR, "index.pkl"), "wb") as f:
        pickle.dump({"data": entries, "model": MODEL_NAME}, f)
    print(f"[ingest] Indexed {len(entries)} items → {FAISS_DIR}")

if __name__ == "__main__":
    rebuild()
