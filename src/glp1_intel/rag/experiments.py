"""Generate every notebook-14 answer once (≈1 h on CPU) and cache it, so the notebook loads instead of regenerating.

    python -m glp1_intel.rag.experiments        (resumable: finished items are skipped)
    → reports/evaluation/nb14_answers.jsonl      one line per answer: kind, question, answer, source chunk ids
"""
import json
import time

import pandas as pd

from glp1_intel.nlp.classical import EVAL_DIR
from glp1_intel.paths import PROCESSED
from glp1_intel.rag import eval_questions as E, generate as G, knowledge_base as K, retrieval as R

OUT = EVAL_DIR / "nb14_answers.jsonl"
SEARCH = dict(source="label", method="hybrid", rerank=True)       # the setup chosen in notebook 13


def brief_doctors() -> pd.DataFrame:
    """Doctor A: top-ranked doctor already prescribing oral semaglutide (Foundayo is oral).
    Doctor B: top-ranked doctor with research papers (a different conversation)."""
    t = pd.read_parquet(PROCESSED / "targeting_scores.parquet").sort_values("rank")
    topics = pd.read_parquet(PROCESSED / "doctor_research_topics.parquet")
    t = t.merge(topics, on="npi", how="left")
    a = t[t["rybelsus_claims"] > 0].iloc[0]
    b = t[t["research_themes"].notna() & (t["npi"] != a["npi"])].iloc[0]
    return pd.DataFrame([a, b]).assign(doctor=["Doctor A", "Doctor B"]).reset_index(drop=True)


def load() -> pd.DataFrame:
    return pd.read_json(OUT, lines=True) if OUT.exists() else pd.DataFrame()


def run() -> None:
    done = set(load()[["kind", "question"]].itertuples(index=False, name=None)) if OUT.exists() else set()
    ret = R.Retriever(K.build())
    jobs = ([("rag", b, q) for b, q, *_ in E.LABEL_QUESTIONS] + [("closed_book", b, q) for b, q, *_ in E.LABEL_QUESTIONS]
            + [("guardrail", b, q) for b, q, _ in E.GUARDRAIL_QUESTIONS])
    with OUT.open("a", encoding="utf-8") as f:
        for kind, brand, q in jobs:
            if (kind, q) in done:
                continue
            t0 = time.time()
            res = G.answer(q, closed_book=True) if kind == "closed_book" else G.answer(q, ret, brand=brand, **SEARCH)
            rec = {"kind": kind, "brand": brand, "question": q, "answer": res["answer"], "seconds": round(time.time() - t0, 1),
                   "sources": res["sources"]["chunk_id"].tolist() if len(res["sources"]) else []}
            f.write(json.dumps(rec) + "\n"); f.flush()
            print(kind, rec["seconds"], "s |", q, flush=True)
        for row in brief_doctors().to_dict("records"):
            if ("brief", row["doctor"]) in done:
                continue
            t0 = time.time()
            b = G.pre_visit_brief(row, ret)
            rec = {"kind": "brief", "brand": "foundayo", "question": row["doctor"], "answer": G.brief_markdown(b, row["doctor"]),
                   "seconds": round(time.time() - t0, 1), "profile": b["profile"],
                   "parts": [{"part": "key facts", "text": b["points"], "sources": b["points_sources"]["chunk_id"].tolist()},
                             {"part": "safety", "text": b["safety"], "sources": b["safety_sources"]["chunk_id"].tolist()}]
                            + [{"part": f"concern: {c}", "text": r["answer"], "sources": r["sources"]["chunk_id"].tolist()}
                               for c, r in zip(b["concerns"], b["replies"])],
                   "sources": b["notes"]["chunk_id"].tolist()}
            f.write(json.dumps(rec) + "\n"); f.flush()
            print("brief", rec["seconds"], "s |", row["doctor"], flush=True)
    print("ALL DONE", flush=True)


if __name__ == "__main__":
    run()
