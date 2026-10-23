"""Analyse one visit note with the models from notebooks 11–12 (used by the rep view of the app).

    entities    BiomedBERT NER (notebook 12): DRUG, ADVERSE_EVENT, DOSE spans
    ae_mode     BiomedBERT classifier (notebook 11): none / concern / reported / negated
    objections  TF-IDF + one-vs-rest logistic regression (notebook 11's best model for objections), refit in seconds
    ade         BiomedBERT ADE sentence detector (notebook 12) at the ≥90%-recall threshold chosen on validation
"""
import json
import re
from functools import lru_cache

import numpy as np

from glp1_intel.models import finetune as FT
from glp1_intel.paths import ROOT

MODELS = ROOT / "models"
EVAL = ROOT / "reports" / "evaluation"


def available() -> dict:
    """Which saved models exist (they are git-ignored, so a fresh clone has none until notebooks 11–12 are run)."""
    return {"ner": (MODELS / "visit_note_ner_biomedbert").exists(), "ae_mode": (MODELS / "visit_note_ae_mode_biomedbert").exists(),
            "ade": (MODELS / "ade_sentence_biomedbert").exists(), "objections": FT.DATA.exists()}


@lru_cache(maxsize=None)
def _ner():
    from transformers import pipeline
    return pipeline("token-classification", model=str(MODELS / "visit_note_ner_biomedbert"), aggregation_strategy="first")


@lru_cache(maxsize=None)
def _clf(name: str):
    from transformers import pipeline
    return pipeline("text-classification", model=str(MODELS / name), top_k=None)


@lru_cache(maxsize=None)
def _objections():
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.multiclass import OneVsRestClassifier
    from sklearn.pipeline import make_pipeline
    tr = FT.load()["train"]
    model = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True),
                          OneVsRestClassifier(LogisticRegression(C=4, max_iter=3000, class_weight="balanced")))
    return model.fit(tr["note"], FT.targets(tr, "objections"))


@lru_cache(maxsize=None)
def ade_threshold() -> float:
    return float(json.loads((EVAL / "nb12_ade.json").read_text())["test_recall90"]["threshold"])


def _label_index(label: str, labels: list[str]) -> int:
    m = re.search(r"(\d+)$", label)
    return int(m.group(1)) if m else labels.index(label)


def analyze(note: str) -> dict:
    av = available()
    out = {"entities": [], "ae_mode": None, "objections": [], "ade_sentences": []}
    if av["ner"]:
        out["entities"] = [{"start": int(e["start"]), "end": int(e["end"]), "label": e["entity_group"],
                            "text": note[e["start"]:e["end"]], "score": float(e["score"])} for e in _ner()(note)]
    if av["ae_mode"]:
        probs = {FT.AE_LABELS[_label_index(p["label"], FT.AE_LABELS)]: float(p["score"])
                 for p in _clf("visit_note_ae_mode_biomedbert")(note)[0]}
        out["ae_mode"] = max(probs, key=probs.get)
        out["ae_mode_probs"] = probs
    if av["objections"]:
        p = _objections().predict_proba([note])[0]
        out["objections"] = [{"objection": k, "prob": float(v)} for k, v in sorted(zip(FT.OBJ_LABELS, p), key=lambda x: -x[1]) if v >= 0.5]
    if av["ade"]:
        # split into sentences, but not after "Dr." / "pt." (common in rep notes)
        sents = [s.strip() for s in re.split(r"(?<=[.!?])(?<!Dr\.)(?<!pt\.)\s+|\n+|\s-\s", note) if len(s.strip()) > 3]
        clf, thr = _clf("ade_sentence_biomedbert"), ade_threshold()
        for s, pr in zip(sents, clf(sents)):
            pos = next((x["score"] for x in pr if _label_index(x["label"], ["0", "1"]) == 1), 0.0)
            out["ade_sentences"].append({"sentence": s, "prob": float(pos), "flag": pos >= thr})
    # Pharmacovigilance triage: a reported AE or any flagged sentence means the note should go to safety review
    out["pv_flag"] = out["ae_mode"] == "reported" or any(s["flag"] for s in out["ade_sentences"])
    return out


def highlight_html(note: str, entities: list[dict]) -> str:
    """The note with entity spans coloured: drugs violet, adverse events coral, doses amber."""
    import html
    style = {"DRUG": ("#EFEAFF", "#4B32C8"), "ADVERSE_EVENT": ("#FFE6DE", "#A63A1A"), "DOSE": ("#FFF3D6", "#8A5A00")}
    parts, last = [], 0
    for e in sorted(entities, key=lambda e: e["start"]):
        if e["start"] < last:
            continue
        bg, fg = style.get(e["label"], ("#eee", "#333"))
        parts += [html.escape(note[last:e["start"]]),
                  f'<mark style="background:{bg};color:{fg};padding:1px 5px;border-radius:6px;font-weight:600" '
                  f'title="{e["label"]} · {e["score"]:.2f}">{html.escape(note[e["start"]:e["end"]])}'
                  f'<sup style="font-size:9px;margin-left:3px">{e["label"].replace("ADVERSE_EVENT", "AE")}</sup></mark>']
        last = e["end"]
    parts.append(html.escape(note[last:]))
    return '<div style="line-height:2;font-size:15px;white-space:pre-wrap">' + "".join(parts) + "</div>"
