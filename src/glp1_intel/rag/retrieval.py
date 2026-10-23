"""Retrieval over the knowledge base (notebook 13), reused by RAG (notebook 14) and the app.

Methods: BM25 (keywords) · dense (sentence embeddings, cosine) · hybrid (reciprocal rank fusion) · cross-encoder re-ranking.
Embeddings are cached in data/02_interim/kb_emb_<model>.npy (MiniLM ~5 min, BGE-small ~10 min on CPU).
"""
import re
from functools import lru_cache

import numpy as np
import pandas as pd

from glp1_intel.paths import INTERIM

MODELS = {
    # key: (Hugging Face id, prefix added to queries only, max tokens the model reads)
    "minilm": ("sentence-transformers/all-MiniLM-L6-v2", "", 256),
    "bge": ("BAAI/bge-small-en-v1.5", "Represent this sentence for searching relevant passages: ", 512),
}
RERANKER = "cross-encoder/ms-marco-MiniLM-L-6-v2"
TOKEN = re.compile(r"(?u)\b\w\w+\b")      # same tokens as the TF-IDF models (hyphens split)


def tokenize(text: str) -> list[str]:
    return TOKEN.findall(text.lower())


@lru_cache(maxsize=None)
def encoder(key: str):
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODELS[key][0])


@lru_cache(maxsize=None)
def cross_encoder():
    from sentence_transformers import CrossEncoder
    return CrossEncoder(RERANKER)


def embed_texts(texts, key: str, query: bool = False) -> np.ndarray:
    """L2-normalised float32 embeddings, so a dot product equals cosine similarity."""
    prefix = MODELS[key][1] if query else ""
    return encoder(key).encode([prefix + t for t in texts], batch_size=64, normalize_embeddings=True,
                               show_progress_bar=False).astype("float32")


def embed_kb(kb: pd.DataFrame, key: str, overwrite: bool = False) -> np.ndarray:
    """Embeddings of every chunk, cached; the cache is rebuilt if the chunk list changed."""
    f, ids = INTERIM / f"kb_emb_{key}.npy", INTERIM / f"kb_emb_{key}_ids.txt"
    if f.exists() and ids.exists() and not overwrite and ids.read_text(encoding="utf-8").splitlines() == kb["chunk_id"].tolist():
        return np.load(f)
    emb = embed_texts(kb["text"].tolist(), key)
    np.save(f, emb)
    ids.write_text("\n".join(kb["chunk_id"]), encoding="utf-8")
    return emb


def faiss_index(emb: np.ndarray, kind: str = "flat"):
    """Exact inner-product search (flat) or approximate graph search (HNSW, 32 links per node)."""
    import faiss
    if kind == "flat":
        index = faiss.IndexFlatIP(emb.shape[1])
    else:
        index = faiss.IndexHNSWFlat(emb.shape[1], 32, faiss.METRIC_INNER_PRODUCT)
        index.hnsw.efSearch = 64
    index.add(emb)
    return index


def rrf(rankings: list[list[int]], k: int = 60) -> list[int]:
    """Reciprocal rank fusion: score = Σ 1 / (k + rank). Uses only ranks, so BM25 and cosine scales never mix."""
    score = {}
    for ranking in rankings:
        for r, i in enumerate(ranking):
            score[i] = score.get(i, 0.0) + 1.0 / (k + r + 1)
    return sorted(score, key=score.get, reverse=True)


class Retriever:
    """All retrieval methods over one knowledge base, with metadata filters (source, brand)."""

    def __init__(self, kb: pd.DataFrame, models=("minilm", "bge")):
        from rank_bm25 import BM25Okapi
        self.kb = kb.reset_index(drop=True)
        self.bm25 = BM25Okapi([tokenize(t) for t in self.kb["text"]])
        self.emb = {m: embed_kb(self.kb, m) for m in models}

    def _mask(self, source=None, brand=None) -> np.ndarray:
        m = np.ones(len(self.kb), bool)
        if source:
            m &= self.kb["source"].isin([source] if isinstance(source, str) else source).values
        if brand:
            m &= (self.kb["brand"] == brand.lower()).values
        return m

    def _top(self, scores: np.ndarray, mask: np.ndarray, k: int) -> list[int]:
        scores = np.where(mask, scores, -np.inf)
        top = np.argpartition(-scores, min(k, len(scores) - 1))[:k]
        return [int(i) for i in top[np.argsort(-scores[top])] if mask[i]]

    def ranked(self, query: str, method: str = "hybrid", k: int = 10, source=None, brand=None,
               rerank: bool = False, pool: int = 30, qemb: dict | None = None) -> list[int]:
        """Row positions of the top-k chunks. method: 'bm25', a model key ('minilm', 'bge') or 'hybrid' (bm25 + bge)."""
        mask = self._mask(source, brand)
        n = pool if rerank or method == "hybrid" else k

        def dense(m):
            q = qemb[m] if qemb and m in qemb else embed_texts([query], m, query=True)[0]
            return self._top(self.emb[m] @ q, mask, n)

        if method == "bm25":
            ids = self._top(self.bm25.get_scores(tokenize(query)), mask, n)
        elif method == "hybrid":
            ids = rrf([self._top(self.bm25.get_scores(tokenize(query)), mask, n), dense("bge")])[:n]
        else:
            ids = dense(method)
        if rerank:
            s = cross_encoder().predict([(query, self.kb.at[i, "text"]) for i in ids], show_progress_bar=False)
            ids = [ids[j] for j in np.argsort(-s)]
        return ids[:k]

    def search(self, query: str, k: int = 5, **kw) -> pd.DataFrame:
        ids = self.ranked(query, k=k, **kw)
        return self.kb.iloc[ids].assign(rank=range(1, len(ids) + 1))


def recall_at_k(ranked: list[list], gold: list[set], k: int) -> float:
    """Share of queries with at least one relevant chunk in the top k (the RAG generator only sees the top k)."""
    return float(np.mean([bool(set(r[:k]) & g) for r, g in zip(ranked, gold)]))


def mrr(ranked: list[list], gold: list[set], k: int = 10) -> float:
    """Mean reciprocal rank of the first relevant chunk (0 if none in the top k)."""
    return float(np.mean([next((1 / (i + 1) for i, x in enumerate(r[:k]) if x in g), 0.0) for r, g in zip(ranked, gold)]))
