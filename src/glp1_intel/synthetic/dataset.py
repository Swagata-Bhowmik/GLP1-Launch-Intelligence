"""Turn generated notes into the labelled visit-notes dataset (classification labels + NER spans + BIO tags).

Labels come from the scenario (fixed before generation). Entity spans come from deterministic string
matching against known lexicons, never from the generator, so every span is exactly where the text is.
"""
import json
import re

import numpy as np
import pandas as pd

from ..paths import ROOT
from . import gate

DIR = ROOT / "data" / "04_synthetic_visit_notes"
RAW_NOTES = DIR / "notes_raw.jsonl"
DATASET = DIR / "visit_notes_v1.parquet"
DATASET_JSONL = DIR / "visit_notes_v1.jsonl"
SAMPLE_BLIND = DIR / "hand_label_sample_v1.csv"          # what Swagata labels (no answers inside)
SAMPLE_KEY = DIR / "hand_label_key_v1.csv"               # the scenario labels, for scoring afterwards

DRUGS = gate.BRANDS + ["tirzepatide", "semaglutide", "dulaglutide", "liraglutide", "orforglipron", "exenatide",
                       "metformin", "insulin"]
DOSE = re.compile(r"(?<![\w.])\d+(?:\.\d+)?\s?(?:mg|mcg|ug|units?)\b", re.I)
# Side-effect lexicon for tagging. Efficacy words (weight loss, appetite, glucose) are left out on purpose:
# in GLP-1 notes they are usually the intended effect, so they're tagged only when they are the scenario's term.
AE_LEXICON = sorted({w for k, ws in gate.AE_ALIASES.items()
                     if k not in ("weight decreased", "weight increased", "blood glucose increased", "decreased appetite",
                                  "vision loss", "depression", "thyroid tumours")
                     for w in ws if len(w) > 3}, key=len, reverse=True)
TOKEN = re.compile(r"\w+(?:[-.']\w+)*|[^\w\s]")
OBJECTION_KEYS = ["cost_coverage", "gi_tolerability", "elderly_frailty", "efficacy_vs_comp", "injection_aversion",
                  "supply_access", "safety_other"]


def entity_spans(note: str, scenario: dict) -> list[dict]:
    """DRUG, DOSE and ADVERSE_EVENT spans; overlapping matches keep the longest."""
    found = []
    for label, words in [("DRUG", DRUGS), ("ADVERSE_EVENT", AE_LEXICON + gate.aliases(scenario.get("ae_term", "")))]:
        found += [(s, e, label) for s, e in gate.find_mentions(note, words)]
    found += [(m.start(), m.end(), "DOSE") for m in DOSE.finditer(note)]
    found.sort(key=lambda t: (t[0], -(t[1] - t[0])))
    out, last_end = [], -1
    for s, e, label in found:
        if s >= last_end:                                   # drop spans nested inside a longer one
            out.append({"start": s, "end": e, "label": label, "text": note[s:e]})
            last_end = e
    return out


def bio(note: str, spans: list[dict]) -> tuple[list[str], list[str]]:
    """Word tokens and BIO tags (B- = first token of an entity, I- = inside, O = outside)."""
    tokens, tags = [], []
    for m in TOKEN.finditer(note):
        tag = "O"
        for sp in spans:
            if sp["start"] <= m.start() < sp["end"]:
                tag = ("B-" if m.start() == sp["start"] or not tags or tags[-1] == "O" else "I-") + sp["label"]
                break
        tokens.append(m.group())
        tags.append(tag)
    return tokens, tags


def build(seed: int = 42) -> pd.DataFrame:
    recs = [json.loads(line) for line in RAW_NOTES.open(encoding="utf-8")]
    kept = [r for r in recs if r["passed"] and not gate.check(r["note"], r)]
    rows = []
    for r in kept:
        sp = entity_spans(r["note"], r)
        tokens, tags = bio(r["note"], sp)
        rows.append({
            "note_id": r["scenario_id"], "note": r["note"],
            "specialty": r["specialty"], "state": r["state"], "rep_portfolio": r["rep_portfolio"],
            "products_discussed": r["products_discussed"], "competitor_mentions": r["competitor_mentions"],
            "interest_level": r["interest_level"], "objections": r["objections"],
            **{f"obj_{k}": int(k in r["objections"]) for k in OBJECTION_KEYS},
            "ae_mode": r["ae_mode"], "ae_term": r["ae_term"], "ae_drug": r["ae_drug"],
            "ae_reported": int(r["ae_mode"] == "reported"),
            "entities": sp, "tokens": tokens, "ner_tags": tags,
            "style": r["style"], "generation_attempt": r["attempt"],
        })
    df = pd.DataFrame(rows)
    rng = np.random.default_rng(seed)
    df["split"] = rng.choice(["train", "validation", "test"], size=len(df), p=[0.7, 0.15, 0.15])
    df.to_parquet(DATASET, index=False)
    df.to_json(DATASET_JSONL, orient="records", lines=True, force_ascii=False)
    return df


def hand_label_sample(df: pd.DataFrame, n: int = 100, seed: int = 0) -> pd.DataFrame:
    """Blind sample (note text only + empty columns to fill) and a separate answer key."""
    s = df[df["split"] == "test"].sample(n, random_state=seed)
    blind = s[["note_id", "note"]].assign(
        interest_high_medium_low="", side_effect_reported_yes_no="", side_effect_negated_yes_no="",
        competitor_brands_mentioned="", notes_or_doubts="")
    blind.to_csv(SAMPLE_BLIND, index=False, encoding="utf-8-sig")       # utf-8-sig so Excel shows · and – correctly
    s[["note_id", "interest_level", "ae_mode", "ae_reported", "competitor_mentions", "objections"]].to_csv(
        SAMPLE_KEY, index=False, encoding="utf-8-sig")
    return blind
