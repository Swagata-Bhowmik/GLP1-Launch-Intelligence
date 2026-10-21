"""Fine-tune BERT vs BiomedBERT on the synthetic visit notes, with a TF-IDF baseline for comparison.

Tasks
    ae_mode     single-label, 4 classes: none / concern / reported / negated  (pharmacovigilance-relevant)
    objections  multi-label, 7 objection types (a note can have 0, 1 or 2)

Each run writes reports/evaluation/nb11_<task>__<model>.json (validation curve, test metrics, test predictions),
so notebook 11 can load results instead of retraining. Run all experiments (≈1.5 h on CPU):
    python -m glp1_intel.models.finetune
"""
import copy
import json
import sys
import time

import numpy as np
import pandas as pd
import torch
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.multiclass import OneVsRestClassifier

from ..paths import ROOT

DATA = ROOT / "data" / "04_synthetic_visit_notes" / "visit_notes_v1.jsonl"
EVAL_DIR = ROOT / "reports" / "evaluation"
MODEL_DIR = ROOT / "models"
MODELS = {"bert": "bert-base-uncased",
          "biomedbert": "microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext"}
AE_LABELS = ["none", "concern", "reported", "negated"]
OBJ_LABELS = ["cost_coverage", "gi_tolerability", "elderly_frailty", "efficacy_vs_comp", "injection_aversion",
              "supply_access", "safety_other"]
SEED = 42


def load() -> dict[str, pd.DataFrame]:
    df = pd.read_json(DATA, lines=True)
    return {s: df[df["split"] == s].reset_index(drop=True) for s in ["train", "validation", "test"]}


def targets(df: pd.DataFrame, task: str) -> np.ndarray:
    if task == "ae_mode":
        return df["ae_mode"].map(AE_LABELS.index).to_numpy()
    return df[[f"obj_{k}" for k in OBJ_LABELS]].to_numpy(dtype=np.float32)


def score(task: str, y_true, y_pred) -> dict:
    """Macro-F1 = average F1 over classes, so rare classes count as much as common ones."""
    if task == "ae_mode":
        return {"macro_f1": f1_score(y_true, y_pred, average="macro"),
                "accuracy": float((y_true == y_pred).mean()),
                "per_class": classification_report(y_true, y_pred, target_names=AE_LABELS, output_dict=True,
                                                   zero_division=0),
                "confusion": confusion_matrix(y_true, y_pred, labels=range(4)).tolist()}
    return {"macro_f1": f1_score(y_true, y_pred, average="macro", zero_division=0),
            "micro_f1": f1_score(y_true, y_pred, average="micro", zero_division=0),
            "exact_match": float((y_true == y_pred).all(axis=1).mean()),
            "per_class": classification_report(y_true, y_pred, target_names=OBJ_LABELS, output_dict=True,
                                               zero_division=0)}


def bootstrap_ci(task: str, y_true, y_pred, n: int = 1000, seed: int = 0) -> list[float]:
    """95% confidence interval for macro-F1 by resampling the test set (it has only ~158 notes)."""
    rng = np.random.default_rng(seed)
    stats = []
    for _ in range(n):
        i = rng.integers(0, len(y_true), len(y_true))
        stats.append(score(task, y_true[i], y_pred[i])["macro_f1"])
    return [float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5))]


def tfidf_baseline(task: str) -> dict:
    d = load()
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
    Xtr, Xte = vec.fit_transform(d["train"]["note"]), vec.transform(d["test"]["note"])
    ytr, yte = targets(d["train"], task), targets(d["test"], task)
    clf = LogisticRegression(C=4, max_iter=3000, class_weight="balanced")
    if task == "objections":
        clf = OneVsRestClassifier(clf)
    pred = clf.fit(Xtr, ytr).predict(Xte)
    return _save(task, "tfidf", {"test": score(task, yte, pred), "ci95": bootstrap_ci(task, yte, pred),
                                 "pred": np.asarray(pred).tolist(), "curve": []})


class _Notes(torch.utils.data.Dataset):
    def __init__(self, enc, y):
        self.enc, self.y = enc, y

    def __len__(self):
        return len(self.y)

    def __getitem__(self, i):
        item = {k: torch.tensor(v[i]) for k, v in self.enc.items()}
        item["labels"] = torch.tensor(self.y[i])
        return item


def train(task: str, model_key: str, epochs: int = 4, lr: float = 3e-5, batch_size: int = 16,
          max_length: int = 160, save_model: bool = False, smoke: int = 0) -> dict:
    """Fine-tune one model on one task; keep the best validation epoch in memory (no checkpoints on disk)."""
    from transformers import (AutoModelForSequenceClassification, AutoTokenizer, DataCollatorWithPadding,
                              Trainer, TrainerCallback, TrainingArguments, set_seed)
    set_seed(SEED)
    d = load()
    if smoke:                                               # tiny run to catch API problems quickly
        d = {k: v.head(smoke) for k, v in d.items()}
    name = MODELS[model_key]
    tok = AutoTokenizer.from_pretrained(name)
    multi = task == "objections"
    model = AutoModelForSequenceClassification.from_pretrained(
        name, num_labels=len(OBJ_LABELS) if multi else len(AE_LABELS),
        problem_type="multi_label_classification" if multi else "single_label_classification")

    def ds(split):
        enc = tok(d[split]["note"].tolist(), truncation=True, max_length=max_length)   # padding per batch
        return _Notes(enc, targets(d[split], task))

    def predict_labels(logits):
        return (1 / (1 + np.exp(-logits)) >= 0.5).astype(int) if multi else logits.argmax(-1)

    def compute_metrics(p):
        return {"macro_f1": score(task, p.label_ids.astype(int) if multi else p.label_ids,
                                  predict_labels(p.predictions))["macro_f1"]}

    class KeepBest(TrainerCallback):
        """Copy the weights whenever validation macro-F1 improves; restore them at the end (early-stopping style)."""
        def __init__(self):
            self.best, self.state_dict, self.curve = -1, None, []

        def on_evaluate(self, args, state, control, metrics=None, **kw):
            self.curve.append({"epoch": round(state.epoch), "val_macro_f1": metrics["eval_macro_f1"],
                               "val_loss": metrics["eval_loss"]})
            if metrics["eval_macro_f1"] > self.best:
                self.best = metrics["eval_macro_f1"]
                self.state_dict = copy.deepcopy(kw["model"].state_dict())

    keep = KeepBest()
    args = TrainingArguments(output_dir=str(MODEL_DIR / "_tmp"), num_train_epochs=epochs, learning_rate=lr,
                             per_device_train_batch_size=batch_size, per_device_eval_batch_size=32,
                             warmup_steps=int(0.1 * epochs * -(-len(d["train"]) // batch_size)),   # 10% warm-up
                             weight_decay=0.01, eval_strategy="epoch", save_strategy="no",
                             logging_strategy="epoch", report_to=[], seed=SEED, disable_tqdm=True)
    trainer = Trainer(model=model, args=args, train_dataset=ds("train"), eval_dataset=ds("validation"),
                      data_collator=DataCollatorWithPadding(tok), compute_metrics=compute_metrics, callbacks=[keep])
    t0 = time.time()
    trainer.train()
    model.load_state_dict(keep.state_dict)
    test = trainer.predict(ds("test"))
    y_true = test.label_ids.astype(int) if multi else test.label_ids
    pred = predict_labels(test.predictions)
    if save_model:
        out = MODEL_DIR / f"visit_note_{task}_{model_key}"
        model.save_pretrained(out)
        tok.save_pretrained(out)
    if smoke:
        return {"smoke_ok": True, "curve": keep.curve}
    return _save(task, model_key, {"test": score(task, y_true, pred), "ci95": bootstrap_ci(task, y_true, pred),
                                   "pred": np.asarray(pred).tolist(), "curve": keep.curve,
                                   "train_minutes": round((time.time() - t0) / 60, 1), "epochs": epochs, "lr": lr})


def _save(task: str, model_key: str, payload: dict) -> dict:
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    (EVAL_DIR / f"nb11_{task}__{model_key}.json").write_text(json.dumps(payload, indent=1, default=float))
    return payload


def result(task: str, model_key: str) -> dict | None:
    f = EVAL_DIR / f"nb11_{task}__{model_key}.json"
    return json.loads(f.read_text()) if f.exists() else None


if __name__ == "__main__":
    torch.set_num_threads(4)
    for task in ["ae_mode", "objections"]:
        tfidf_baseline(task)
        print(f"{task} tfidf done", flush=True)
        for key in ["bert", "biomedbert"]:
            if result(task, key) is None:
                r = train(task, key, save_model=(task == "ae_mode" and key == "biomedbert"))
                print(f"{task} {key}: test macro-F1 {r['test']['macro_f1']:.3f} ({r['train_minutes']} min)", flush=True)
    sys.exit(0)
