"""Word embeddings (Word2Vec, fastText) and topic models (LDA, BERTopic) on the PubMed corpus.

Outputs used later:
    data/02_interim/pubmed_embeddings_minilm.npy     sentence embeddings (cached: ~5 min on CPU)
    data/03_processed/pubmed_topics.parquet           one row per abstract with its BERTopic topic
    data/03_processed/doctor_research_topics.parquet  research themes of name-linked doctors (KOL profile)
"""
import re

import nltk
import numpy as np
import pandas as pd

from ..paths import INTERIM, PROCESSED
from . import preprocess as P

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMB_FILE = INTERIM / "pubmed_embeddings_minilm.npy"
TOPICS_FILE = PROCESSED / "pubmed_topics.parquet"
DOCTOR_TOPICS_FILE = PROCESSED / "doctor_research_topics.parquet"
SEED = 42


def abstracts() -> pd.DataFrame:
    """PubMed abstracts in a fixed order (the embedding cache relies on this order)."""
    c = P.build_corpus()
    ab = c[c["source"] == "pubmed"].reset_index(drop=True)
    ab["doc"] = ab["title"] + ". " + ab["text"]
    return ab


def w2v_sentences(texts) -> list[list[str]]:
    """Lower-cased word tokens per sentence; hyphenated drug names kept whole for embeddings."""
    return [re.findall(r"[a-z0-9][a-z0-9\-]*", s.lower()) for t in texts for s in nltk.sent_tokenize(t)]


def add_phrases(sentences, min_count: int = 20, threshold: float = 10):
    """Join frequent collocations into one token: weight loss → weight_loss (gensim Phrases, PMI-like score)."""
    from gensim.models.phrases import ENGLISH_CONNECTOR_WORDS, Phrases
    ph = Phrases(sentences, min_count=min_count, threshold=threshold, connector_words=ENGLISH_CONNECTOR_WORDS)
    return [ph[s] for s in sentences], ph


def embed(docs: list[str], overwrite: bool = False) -> np.ndarray:
    """Sentence-transformer embeddings for every abstract, cached to disk."""
    if EMB_FILE.exists() and not overwrite:
        emb = np.load(EMB_FILE)
        if len(emb) == len(docs):
            return emb
    from sentence_transformers import SentenceTransformer
    emb = SentenceTransformer(EMBED_MODEL).encode(docs, batch_size=64, show_progress_bar=False)
    np.save(EMB_FILE, emb)
    return emb


def fit_bertopic(docs: list[str], emb: np.ndarray, min_cluster_size: int = 40):
    """BERTopic = embeddings → UMAP (reduce to 5-D) → HDBSCAN (density clusters) → c-TF-IDF (topic words)."""
    from bertopic import BERTopic
    from hdbscan import HDBSCAN
    from sklearn.feature_extraction.text import CountVectorizer
    from umap import UMAP
    model = BERTopic(
        umap_model=UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric="cosine", random_state=SEED),
        hdbscan_model=HDBSCAN(min_cluster_size=min_cluster_size, metric="euclidean",
                              cluster_selection_method="eom", prediction_data=True),
        vectorizer_model=CountVectorizer(stop_words="english", ngram_range=(1, 2), min_df=5),
        top_n_words=8, verbose=False)
    topics, _ = model.fit_transform(docs, emb)
    return model, np.array(topics)


def topic_label(model, topic_id: int, n: int = 4) -> str:
    """Readable label from the top c-TF-IDF words, e.g. 'optic · neuropathy · risk · optic neuropathy'."""
    if topic_id == -1:
        return "outliers (no clear topic)"
    return " · ".join(w for w, _ in model.get_topic(topic_id)[:n])


def doctor_topics(doc_topics: pd.DataFrame) -> pd.DataFrame:
    """Research themes per doctor, via the name-matched PubMed authors from notebook 05."""
    links = pd.read_parquet(INTERIM / "pubmed_author_npi_links.parquet")
    links = links[links["match"] == "matched"][["pmid", "npi"]].drop_duplicates()
    d = links.merge(doc_topics[["pmid", "topic", "topic_label"]], on="pmid")
    d = d[d["topic"] != -1]
    g = (d.groupby(["npi", "topic", "topic_label"]).size().rename("papers").reset_index()
          .sort_values(["npi", "papers"], ascending=[True, False]))
    top = g.groupby("npi").head(3).groupby("npi").agg(
        n_topic_papers=("papers", "sum"), research_themes=("topic_label", lambda s: " | ".join(s))).reset_index()
    top.to_parquet(DOCTOR_TOPICS_FILE, index=False)
    return top
