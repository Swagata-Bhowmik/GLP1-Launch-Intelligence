"""Classical NLP baselines: Bag-of-Words / TF-IDF features + Naive Bayes, Logistic Regression, Linear SVM.

Task: adverse-drug-event (ADE) sentence detection on ADE Corpus v2 (1 = sentence describes a drug side effect).
These baselines are the bar the fine-tuned transformer (notebook 12) has to beat, so every metric is saved
to reports/evaluation/ in a fixed format.
"""
import json

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, confusion_matrix, f1_score, precision_recall_curve,
                             precision_score, recall_score, roc_auc_score, accuracy_score)
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

from ..paths import RAW, ROOT

ADE_FILE = RAW / "ade_corpus_training_data/ade_corpus_v2_classification.parquet"
EVAL_DIR = ROOT / "reports" / "evaluation"
SEED = 42


def load_ade(dedupe: bool = True) -> pd.DataFrame:
    """ADE sentences; exact duplicate sentences are dropped so none can sit in both train and test (leakage)."""
    df = pd.read_parquet(ADE_FILE)
    return df.drop_duplicates("text").reset_index(drop=True) if dedupe else df


def split(df: pd.DataFrame, test: float = 0.15, val: float = 0.15):
    """Stratified train / validation / test split (keeps the same positive rate in every part)."""
    train_val, test_df = train_test_split(df, test_size=test, stratify=df["label"], random_state=SEED)
    train_df, val_df = train_test_split(train_val, test_size=val / (1 - test), stratify=train_val["label"],
                                        random_state=SEED)
    return train_df.reset_index(drop=True), val_df.reset_index(drop=True), test_df.reset_index(drop=True)


def pipelines() -> dict[str, Pipeline]:
    """Three classic text classifiers, each with the features that suit it."""
    # Split on hyphens ("mofetil-induced" -> "mofetil", "induced"): keeping hyphenated words whole hid the
    # strongest ADE cue word and cost ~4.5 F1 points (notebook 07, section 5)
    ngram = dict(ngram_range=(1, 2), min_df=2, lowercase=True, token_pattern=r"(?u)\b\w\w+\b")
    return {
        "Naive Bayes (counts)": Pipeline([("vec", CountVectorizer(**ngram)), ("clf", MultinomialNB(alpha=0.5))]),
        "Logistic Regression (TF-IDF)": Pipeline([("vec", TfidfVectorizer(sublinear_tf=True, **ngram)),
                                                  ("clf", LogisticRegression(C=4, max_iter=2000, class_weight="balanced"))]),
        "Linear SVM (TF-IDF)": Pipeline([("vec", TfidfVectorizer(sublinear_tf=True, **ngram)),
                                         ("clf", LinearSVC(C=0.5, class_weight="balanced"))]),
    }


def scores(model, X) -> np.ndarray:
    """A continuous score per sentence (probability if available, else SVM margin)."""
    return model.predict_proba(X)[:, 1] if hasattr(model, "predict_proba") else model.decision_function(X)


def metrics(y_true, y_pred, y_score=None) -> dict:
    out = {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred),
        "recall": recall_score(y_true, y_pred),
        "f1": f1_score(y_true, y_pred),
        "macro_f1": f1_score(y_true, y_pred, average="macro"),
        "weighted_f1": f1_score(y_true, y_pred, average="weighted"),
    }
    if y_score is not None:
        out["roc_auc"] = roc_auc_score(y_true, y_score)
        out["pr_auc"] = average_precision_score(y_true, y_score)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    out.update(tp=int(tp), fp=int(fp), fn=int(fn), tn=int(tn))
    return {k: (round(float(v), 4) if isinstance(v, float) else v) for k, v in out.items()}


def threshold_for_recall(y_true, y_score, target: float = 0.90) -> float:
    """Highest threshold whose recall still meets `target` (chosen on validation data, never on test)."""
    p, r, t = precision_recall_curve(y_true, y_score)
    ok = np.where(r[:-1] >= target)[0]
    return float(t[ok[-1]]) if len(ok) else float(t[0])


def save_metrics(name: str, payload: dict) -> None:
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    (EVAL_DIR / f"{name}.json").write_text(json.dumps(payload, indent=2))
