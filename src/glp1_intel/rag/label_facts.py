"""Verbatim key facts from a drug label (indication, starting dose, boxed warning, common side effects), with citations.

No LLM: sentences are located by pattern and quoted exactly, so the rep view can show an instant, faithful summary.
"""
import re
from functools import lru_cache

from glp1_intel.rag import knowledge_base as K

PATTERNS = [
    ("Indication", "indications_and_usage", r"\b(is|are) indicated\b"),
    ("Starting dose", "dosage_and_administration", r"starting dos|initiate|start(ing)? at|\bstart\b"),
    ("Boxed warning", "boxed_warning", r"."),
    ("Most common side effects", "adverse_reactions", r"most common adverse reactions"),
]


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.;])\s+(?=[A-Z•])", text) if len(s.strip()) > 20]


@lru_cache(maxsize=None)
def key_facts(brand: str) -> list[dict]:
    secs = K.label_sections()
    secs = secs[secs["brand"] == brand.lower()].set_index("section")
    out = []
    for name, sec, pat in PATTERNS:
        if sec not in secs.index:
            continue
        row = secs.loc[sec]
        # drop the label's cross-references first ("( 2.1 )", "[see Warnings ( 5.1 )]"): they block sentence splitting
        text = re.sub(r"\s*\[see [^\]]*\]\s*", " ", row["text"])
        text = re.sub(r"\s*\(\s*[\d.,\s]+\)\s*", " ", text)
        text = re.sub(r"^\s*\d+\s+(INDICATIONS AND USAGE|DOSAGE AND ADMINISTRATION|ADVERSE REACTIONS)\s+", "", text)
        hit = None
        for sent in _sentences(text):
            m = re.search(pat, sent, re.I)
            if m:
                hit = sent[m.start():] if name == "Most common side effects" else sent
                break
        if hit:
            hit = hit[0].upper() + hit[1:]
            d = row["effective_date"]
            out.append({"fact": name, "text": hit[:420] + ("…" if len(hit) > 420 else ""),
                        "source": f"{brand.title()} label · {K.LABEL_SECTIONS[sec]} ({d[:4]}-{d[4:6]})"})
    return out
