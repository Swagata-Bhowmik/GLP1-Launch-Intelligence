"""Text preprocessing for the project's NLP: corpus loading, normalisation, regex extraction, cleaning.

Design choice: **one configurable `clean()` function**, because different models need different cleaning:
    - Bag-of-words / TF-IDF (notebook 07): lower-case, drop stop words, lemmatise, but KEEP negations
    - Transformers (notebooks 10–12): almost no cleaning; their subword tokenizer handles raw text
"""
import json
import re
import unicodedata

import pandas as pd

from ..paths import INTERIM, RAW

CORPUS = INTERIM / "nlp_corpus.parquet"

# ── Unicode: characters that look alike but are different code points ──────
UNICODE_FIXES = {
    " ": " ",   # non-breaking space
    " ": " ",   # thin space
    "–": "-",   # en dash   (5–10 mg)
    "—": "-",   # em dash
    "−": "-",   # minus sign
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "µ": "u",   # micro sign  µg → ug
    "μ": "u",   # Greek mu    μg → ug
    "≥": ">=", "≤": "<=",
}

# ── Regular expressions for clinically meaningful patterns ──────────────────
PATTERNS = {
    "dose":       r"\b\d+(?:\.\d+)?\s?(?:mg|ug|mcg|g|ml|units?|iu)\b",
    "percent":    r"\b\d+(?:\.\d+)?\s?%",
    "hba1c":      r"\bhba1c\b[^.]{0,40}?\b\d+(?:\.\d+)?\s?%",
    "p_value":    r"\bp\s?[<=>]\s?0?\.\d+",
    "trial_name": r"\b(?:SURMOUNT|SURPASS|ATTAIN|ACHIEVE|STEP|SUSTAIN|PIONEER|SELECT|SURMOUNT-OSA|TRIUMPH|FLOW)(?:-[A-Z0-9]+|\s\d+)?\b",
}
# spaCy's general-English lemmatiser makes mistakes on medical words; small domain overrides fix them
LEMMA_OVERRIDES = {"doses": "dose", "dos": "dose", "diabetes": "diabetes", "analogues": "analogue"}
NEGATIONS = {"no", "not", "nor", "without", "never", "none", "neither", "cannot", "n't"}


def normalize_unicode(text: str) -> str:
    """NFKC normalisation + explicit fixes for look-alike characters."""
    text = unicodedata.normalize("NFKC", text or "")
    for bad, good in UNICODE_FIXES.items():
        text = text.replace(bad, good)
    return re.sub(r"\s+", " ", text).strip()


def extract(text: str, kind: str) -> list[str]:
    """All matches of one PATTERNS regex (case-insensitive except trial names)."""
    flags = 0 if kind == "trial_name" else re.IGNORECASE
    return re.findall(PATTERNS[kind], text, flags)


def load_pubmed() -> pd.DataFrame:
    """All downloaded abstracts, one row per paper (papers found by several queries are kept once)."""
    rows = []
    for f in sorted((RAW / "pubmed_research_papers").glob("pubmed_*.jsonl")):
        for line in f.open(encoding="utf-8"):
            p = json.loads(line)
            if p["abstract"]:
                rows.append({"doc_id": f"pmid:{p['pmid']}", "source": "pubmed", "query": p["query"],
                             "year": p["year"], "title": p["title"], "text": p["abstract"]})
    return pd.DataFrame(rows).drop_duplicates("doc_id")


def load_label_sections(sections=("adverse_reactions", "warnings_and_cautions", "indications_and_usage")) -> pd.DataFrame:
    """Selected sections of each brand's own (manufacturer, most recent) label."""
    rows = []
    for f in sorted((RAW / "fda_drug_labels").glob("label_*.json")):
        labels = json.loads(f.read_text(encoding="utf-8"))
        own = [l for l in labels if not any("A-S Medication" in m for m in l["openfda"].get("manufacturer_name", []))]
        if not own:
            continue
        lab = max(own, key=lambda l: l.get("effective_time", ""))
        brand = f.stem.replace("label_", "")
        for sec in sections:
            for i, txt in enumerate(lab.get(sec, [])):
                rows.append({"doc_id": f"label:{brand}:{sec}:{i}", "source": "label", "query": brand,
                             "year": lab.get("effective_time", "")[:4], "title": f"{brand.title()} · {sec}", "text": txt})
    return pd.DataFrame(rows)


def build_corpus(overwrite: bool = False) -> pd.DataFrame:
    """PubMed abstracts + label sections, unicode-normalised, saved for notebooks 07–08."""
    if CORPUS.exists() and not overwrite:
        return pd.read_parquet(CORPUS)
    df = pd.concat([load_pubmed(), load_label_sections()], ignore_index=True)
    df["text"] = df["text"].map(normalize_unicode)
    df.to_parquet(CORPUS, index=False)
    return df


_nlp = None


def spacy_nlp():
    """Load spaCy once (parser and NER disabled when only lemmas are needed is up to the caller)."""
    global _nlp
    if _nlp is None:
        import spacy
        _nlp = spacy.load("en_core_web_sm")
    return _nlp


def clean(text: str, lower: bool = True, remove_stopwords: bool = True, lemmatize: bool = True,
          keep_negations: bool = True, min_len: int = 2) -> list[str]:
    """Normalise → tokenise (spaCy) → optionally lower-case, drop stop words/punctuation, lemmatise.

    Negations are kept by default: "no nausea" and "nausea" must not become the same document.
    """
    doc = spacy_nlp()(normalize_unicode(text))
    out = []
    for t in doc:
        if t.is_punct or t.is_space:
            continue
        word = (LEMMA_OVERRIDES.get(t.lower_, LEMMA_OVERRIDES.get(t.lemma_.lower(), t.lemma_)) if lemmatize else t.text)
        word = word.lower() if lower else word
        is_neg = t.lower_ in NEGATIONS or t.dep_ == "neg"
        if remove_stopwords and t.is_stop and not (keep_negations and is_neg):
            continue
        if len(word) < min_len and not is_neg:
            continue
        out.append(word)
    return out
