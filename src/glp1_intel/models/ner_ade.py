"""Notebook 12: token classification (NER) on visit notes + adverse-drug-event (ADE) sentence detection.

    ner  BiomedBERT tags DRUG / ADVERSE_EVENT / DOSE in the synthetic visit notes (BIO scheme, seqeval metrics)
    ade  BiomedBERT classifies ADE Corpus v2 sentences, on the SAME deduplicated split as notebook 07,
         so its F1 / PR-AUC are directly comparable with the TF-IDF baseline

Results → reports/evaluation/nb12_<task>.json ; run everything (≈1.5 h on CPU):
    python -m glp1_intel.models.ner_ade
"""
import copy
import json
import sys
import time

import numpy as np
import pandas as pd
import torch

from ..nlp import classical as C
from ..paths import ROOT
from .finetune import MODELS, SEED, load as load_notes

EVAL_DIR = ROOT / "reports" / "evaluation"
MODEL_DIR = ROOT / "models"
NER_TAGS = ["O", "B-DRUG", "I-DRUG", "B-ADVERSE_EVENT", "I-ADVERSE_EVENT", "B-DOSE", "I-DOSE"]


def _keep_best_callback(metric: str):
    from transformers import TrainerCallback

    class KeepBest(TrainerCallback):
        def __init__(self):
            self.best, self.state_dict, self.curve = -1, None, []

        def on_evaluate(self, args, state, control, metrics=None, **kw):
            self.curve.append({"epoch": round(state.epoch), f"val_{metric}": metrics[f"eval_{metric}"],
                               "val_loss": metrics["eval_loss"]})
            if metrics[f"eval_{metric}"] > self.best:
                self.best = metrics[f"eval_{metric}"]
                self.state_dict = copy.deepcopy(kw["model"].state_dict())
    return KeepBest()


def _args(epochs, lr, batch_size, n_train):
    from transformers import TrainingArguments
    return TrainingArguments(output_dir=str(MODEL_DIR / "_tmp"), num_train_epochs=epochs, learning_rate=lr,
                             per_device_train_batch_size=batch_size, per_device_eval_batch_size=32,
                             warmup_steps=int(0.1 * epochs * -(-n_train // batch_size)), weight_decay=0.01,
                             eval_strategy="epoch", save_strategy="no", logging_strategy="epoch", report_to=[],
                             seed=SEED, disable_tqdm=True)


class _DS(torch.utils.data.Dataset):
    def __init__(self, enc, labels):
        self.enc, self.labels = enc, labels

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, i):
        item = {k: torch.tensor(v[i]) for k, v in self.enc.items()}
        item["labels"] = torch.tensor(self.labels[i])
        return item


# ── NER on visit notes ──────────────────────────────────────────────────────
def align_labels(enc, word_tags: list[list[str]]) -> list[list[int]]:
    """Sub-word alignment: the first sub-token of each word gets the word's tag; the rest get -100 (ignored by the loss)."""
    out = []
    for i, tags in enumerate(word_tags):
        prev, row = None, []
        for w in enc.word_ids(i):
            row.append(-100 if w is None or w == prev else NER_TAGS.index(tags[w]))
            prev = w
        out.append(row)
    return out


def train_ner(model_key: str = "biomedbert", epochs: int = 5, lr: float = 5e-5, batch_size: int = 16,
              smoke: int = 0, save_model: bool = True) -> dict:
    from seqeval.metrics import classification_report, f1_score
    from transformers import (AutoModelForTokenClassification, AutoTokenizer, DataCollatorForTokenClassification,
                              Trainer, set_seed)
    set_seed(SEED)
    d = load_notes()
    if smoke:
        d = {k: v.head(smoke) for k, v in d.items()}
    name = MODELS[model_key]
    tok = AutoTokenizer.from_pretrained(name)
    model = AutoModelForTokenClassification.from_pretrained(
        name, num_labels=len(NER_TAGS), id2label=dict(enumerate(NER_TAGS)), label2id={t: i for i, t in enumerate(NER_TAGS)})

    def ds(split):
        enc = tok(d[split]["tokens"].tolist(), is_split_into_words=True, truncation=True, max_length=256)
        return _DS(enc, align_labels(enc, d[split]["ner_tags"].tolist())), enc

    def to_tags(pred_ids, label_ids):
        true, pred = [], []
        for p_row, l_row in zip(pred_ids, label_ids):
            keep = [(p, l) for p, l in zip(p_row, l_row) if l != -100]
            true.append([NER_TAGS[l] for _, l in keep])
            pred.append([NER_TAGS[p] for p, _ in keep])
        return true, pred

    def compute_metrics(p):
        true, pred = to_tags(p.predictions.argmax(-1), p.label_ids)
        return {"entity_f1": f1_score(true, pred)}

    keep = _keep_best_callback("entity_f1")
    train_ds, _ = ds("train")
    val_ds, _ = ds("validation")
    test_ds, _ = ds("test")
    trainer = Trainer(model=model, args=_args(epochs, lr, batch_size, len(train_ds)), train_dataset=train_ds,
                      eval_dataset=val_ds, data_collator=DataCollatorForTokenClassification(tok),
                      compute_metrics=compute_metrics, callbacks=[keep])
    t0 = time.time()
    trainer.train()
    model.load_state_dict(keep.state_dict)
    out = trainer.predict(test_ds)
    true, pred = to_tags(out.predictions.argmax(-1), out.label_ids)
    if smoke:
        return {"smoke_ok": True, "curve": keep.curve}
    if save_model:
        model.save_pretrained(MODEL_DIR / f"visit_note_ner_{model_key}")
        tok.save_pretrained(MODEL_DIR / f"visit_note_ner_{model_key}")
    return _save("ner", {"model": model_key, "curve": keep.curve, "test_entity_f1": f1_score(true, pred),
                         "report": classification_report(true, pred, output_dict=True),
                         "examples": [{"tokens": list(t), "true": tt, "pred": pp} for t, tt, pp in
                                      zip(d["test"]["tokens"].head(20), true[:20], pred[:20])],
                         "train_minutes": round((time.time() - t0) / 60, 1)})


# ── ADE sentence detection (ADE Corpus v2) ──────────────────────────────────
def train_ade(model_key: str = "biomedbert", epochs: int = 2, lr: float = 3e-5, batch_size: int = 32,
              smoke: int = 0, save_model: bool = True) -> dict:
    from transformers import (AutoModelForSequenceClassification, AutoTokenizer, DataCollatorWithPadding,
                              Trainer, set_seed)
    set_seed(SEED)
    train_df, val_df, test_df = C.split(C.load_ade())                    # identical split to notebook 07
    if smoke:
        train_df, val_df, test_df = train_df.head(smoke), val_df.head(smoke), test_df.head(smoke)
    name = MODELS[model_key]
    tok = AutoTokenizer.from_pretrained(name)
    model = AutoModelForSequenceClassification.from_pretrained(name, num_labels=2)

    def ds(df):
        return _DS(tok(df["text"].tolist(), truncation=True, max_length=128), df["label"].tolist())

    def compute_metrics(p):
        from sklearn.metrics import f1_score
        return {"f1": f1_score(p.label_ids, p.predictions.argmax(-1))}

    keep = _keep_best_callback("f1")
    trainer = Trainer(model=model, args=_args(epochs, lr, batch_size, len(train_df)), train_dataset=ds(train_df),
                      eval_dataset=ds(val_df), data_collator=DataCollatorWithPadding(tok),
                      compute_metrics=compute_metrics, callbacks=[keep])
    t0 = time.time()
    trainer.train()
    model.load_state_dict(keep.state_dict)
    probs = lambda df: torch.softmax(torch.tensor(trainer.predict(ds(df)).predictions), -1)[:, 1].numpy()
    val_p, test_p = probs(val_df), probs(test_df)
    if smoke:
        return {"smoke_ok": True, "curve": keep.curve}
    thr = C.threshold_for_recall(val_df["label"], val_p, target=0.90)    # same safety policy as notebook 07
    if save_model:
        model.save_pretrained(MODEL_DIR / f"ade_sentence_{model_key}")
        tok.save_pretrained(MODEL_DIR / f"ade_sentence_{model_key}")
    return _save("ade", {"model": model_key, "curve": keep.curve,
                         "test_default": C.metrics(test_df["label"], (test_p >= 0.5).astype(int), test_p),
                         "test_recall90": {**C.metrics(test_df["label"], (test_p >= thr).astype(int), test_p),
                                           "threshold": thr},
                         "test_scores": test_p.round(4).tolist(), "train_minutes": round((time.time() - t0) / 60, 1)})


def _save(task: str, payload: dict) -> dict:
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    (EVAL_DIR / f"nb12_{task}.json").write_text(json.dumps(payload, indent=1, default=float))
    return payload


def result(task: str) -> dict | None:
    f = EVAL_DIR / f"nb12_{task}.json"
    return json.loads(f.read_text()) if f.exists() else None


if __name__ == "__main__":
    torch.set_num_threads(4)
    if result("ner") is None:
        r = train_ner()
        print(f"ner: test entity F1 {r['test_entity_f1']:.3f} ({r['train_minutes']} min)", flush=True)
    if result("ade") is None:
        r = train_ade()
        print(f"ade: test F1 {r['test_default']['f1']:.3f} · PR-AUC {r['test_default']['pr_auc']:.3f} "
              f"({r['train_minutes']} min)", flush=True)
    sys.exit(0)
