"""Knowledge base for retrieval and RAG (notebooks 13–14): FDA label chunks, PubMed abstracts, synthetic visit notes.

    data/03_processed/kb_chunks.parquet   one row per searchable chunk, with metadata for filtering and citations
"""
import json

import pandas as pd

from glp1_intel.nlp import preprocess as P
from glp1_intel.paths import PROCESSED, RAW, ROOT

KB_FILE = PROCESSED / "kb_chunks.parquet"
NOTES_FILE = ROOT / "data" / "04_synthetic_visit_notes" / "visit_notes_v1.jsonl"

# Numbered top-level label sections. Sub-sections (pregnancy, mechanism_of_action, storage_and_handling …) are
# already contained in their parent's text, so indexing both would put every passage in the index twice.
LABEL_SECTIONS = {
    "boxed_warning": "Boxed Warning", "indications_and_usage": "1 Indications and Usage",
    "dosage_and_administration": "2 Dosage and Administration", "dosage_forms_and_strengths": "3 Dosage Forms and Strengths",
    "contraindications": "4 Contraindications", "warnings_and_cautions": "5 Warnings and Precautions",
    "adverse_reactions": "6 Adverse Reactions", "drug_interactions": "7 Drug Interactions",
    "use_in_specific_populations": "8 Use in Specific Populations", "overdosage": "10 Overdosage",
    "description": "11 Description", "clinical_pharmacology": "12 Clinical Pharmacology",
    "nonclinical_toxicology": "13 Nonclinical Toxicology", "clinical_studies": "14 Clinical Studies",
    "how_supplied": "16 How Supplied / Storage",
}
BRANDS = ["foundayo", "mounjaro", "ozempic", "rybelsus", "saxenda", "trulicity", "victoza", "wegovy", "zepbound"]


def pick_label(brand: str, records: list[dict]) -> dict:
    """One label per brand: records naming only this brand first, then the manufacturer's own, then the newest.

    openFDA's "Ozempic" search also returns the oral Rybelsus label (brand list "OZEMPIC, RYBELSUS"); requiring
    every brand name to be this brand keeps the injectable Ozempic label instead.
    """
    def rank(r):
        names = [n.lower() for n in r["openfda"].get("brand_name", [])]
        own = not any("A-S Medication" in m for m in r["openfda"].get("manufacturer_name", []))
        return all(n.startswith(brand) for n in names), own, r.get("effective_time", "")
    return max(records, key=rank)


def label_sections() -> pd.DataFrame:
    """One row per (brand, top-level section) with label metadata for citations."""
    rows = []
    for brand in BRANDS:
        lab = pick_label(brand, json.loads((RAW / "fda_drug_labels" / f"label_{brand}.json").read_text(encoding="utf-8")))
        for sec, name in LABEL_SECTIONS.items():
            if lab.get(sec):
                rows.append({"brand": brand, "section": sec, "section_name": name,
                             "text": P.normalize_unicode(" ".join(lab[sec])),
                             "effective_date": lab.get("effective_time", ""), "set_id": lab.get("set_id", ""),
                             "manufacturer": ", ".join(lab["openfda"].get("manufacturer_name", []))})
    return pd.DataFrame(rows)


def chunk_words(text: str, size: int = 200, overlap: int = 40) -> list[str]:
    """Fixed-size word windows; each chunk repeats the last `overlap` words of the previous one,
    so a sentence cut at a boundary is still complete in one of the two chunks."""
    words = text.split()
    step = size - overlap
    return [" ".join(words[i:i + size]) for i in range(0, max(len(words) - overlap, 1), step)]


def label_chunks(size: int = 200, overlap: int = 40) -> pd.DataFrame:
    rows = []
    for s in label_sections().itertuples():
        for i, txt in enumerate(chunk_words(s.text, size, overlap)):
            rows.append({"chunk_id": f"label:{s.brand}:{s.section}:{i}", "source": "label", "brand": s.brand,
                         "section": s.section, "title": f"{s.brand.title()} label · {s.section_name}",
                         "year": s.effective_date[:4], "text": txt, "effective_date": s.effective_date,
                         "set_id": s.set_id})
    return pd.DataFrame(rows)


def pubmed_chunks() -> pd.DataFrame:
    """One chunk per abstract (abstracts are ~250 words, already a good retrieval unit). Title kept as metadata."""
    df = P.load_pubmed()
    return pd.DataFrame({"chunk_id": df["doc_id"].values, "source": "pubmed", "brand": "", "section": df["query"].values,
                         "title": df["title"].map(P.normalize_unicode).values, "year": df["year"].values,
                         "text": df["text"].map(P.normalize_unicode).values})


def note_chunks() -> pd.DataFrame:
    """Synthetic visit notes (notebook 09), one chunk each, with the generation labels kept for evaluation."""
    notes = pd.read_json(NOTES_FILE, lines=True)
    return pd.DataFrame({"chunk_id": "note:" + notes["note_id"], "source": "note", "brand": "",
                         "section": notes["split"], "title": notes["specialty"] + " · " + notes["state"],
                         "year": "", "text": notes["note"].str.replace("\n", " ", regex=False),
                         "objections": notes["objections"].map(list)})


def build(overwrite: bool = False) -> pd.DataFrame:
    if KB_FILE.exists() and not overwrite:
        return pd.read_parquet(KB_FILE)
    kb = pd.concat([label_chunks(), pubmed_chunks(), note_chunks()], ignore_index=True)
    kb["objections"] = kb["objections"].map(lambda x: list(x) if isinstance(x, list) else [])
    kb.to_parquet(KB_FILE, index=False)
    return kb
