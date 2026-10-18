"""ADE Corpus v2 (Hugging Face): sentences from medical case reports labelled for adverse drug events.

Used later to train / evaluate the side-effect detector (notebook 12).
Dataset card: https://huggingface.co/datasets/ade-benchmark-corpus/ade_corpus_v2
"""
import pandas as pd
from datasets import load_dataset

from ..paths import RAW

OUT_DIR = RAW / "ade_corpus_training_data"
NAME = "ade-benchmark-corpus/ade_corpus_v2"
CONFIGS = ["Ade_corpus_v2_classification", "Ade_corpus_v2_drug_ade_relation", "Ade_corpus_v2_drug_dosage_relation"]


def fetch(overwrite: bool = False) -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sizes = {}
    for cfg in CONFIGS:
        out = OUT_DIR / f"{cfg.lower()}.parquet"
        if out.exists() and not overwrite:
            sizes[cfg] = len(pd.read_parquet(out))
            continue
        ds = load_dataset(NAME, cfg, split="train")
        ds.to_parquet(str(out))
        sizes[cfg] = len(ds)
    return sizes
