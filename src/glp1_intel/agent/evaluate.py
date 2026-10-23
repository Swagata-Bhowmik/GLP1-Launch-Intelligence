"""Agent test set and cached batch run (notebook 15).

    python -m glp1_intel.agent.evaluate      (≈1 h on CPU, resumable) → reports/evaluation/nb15_agent.jsonl
"""
import json
import time

import pandas as pd

from glp1_intel.agent import agent as A
from glp1_intel.agent.tools import BRAND_MOLECULE, _state
from glp1_intel.nlp.classical import EVAL_DIR

OUT = EVAL_DIR / "nb15_agent.jsonl"

# (question, expected tool calls [(tool, {argument: expected value})], type)
QUESTIONS = [
    ("Which endocrinologists in Ohio should we prioritise for Foundayo?", [("top_doctors", {"state": "OH", "specialty": "endocrinology"})], "doctors"),
    ("Show the top 3 family practice doctors in Texas by targeting score.", [("top_doctors", {"state": "TX", "specialty": "family practice", "n": 3})], "doctors"),
    ("Who are the best untapped-potential doctors in Florida?", [("top_doctors", {"state": "FL", "segment": "D"})], "doctors"),
    ("List the top cardiologists in California for GLP-1 targeting.", [("top_doctors", {"state": "CA", "specialty": "cardiology"})], "doctors"),
    ("Where should a new rep in Georgia start? Who are the best GLP-1 prescribers there?", [("top_doctors", {"state": "GA"})], "doctors"),
    ("What is tirzepatide's share of GLP-1 claims in Louisiana?", [("market_summary", {"state": "LA"})], "market"),
    ("How many eligible GLP-1 prescribers are there in New York?", [("market_summary", {"state": "NY"})], "market"),
    ("What share of US GLP-1 claims is oral semaglutide?", [("market_summary", {})], "market"),
    ("What side effects are most reported to FAERS for Ozempic?", [("side_effect_reports", {"drug": "semaglutide"})], "faers"),
    ("How many FAERS reports mention orforglipron so far?", [("side_effect_reports", {"drug": "orforglipron"})], "faers"),
    ("Top 3 reported reactions for Trulicity in FAERS?", [("side_effect_reports", {"drug": "dulaglutide", "top": 3})], "faers"),
    ("What is the starting dose of Foundayo?", [("label_answer", {"brand": "foundayo"})], "label"),
    ("Does Zepbound interact with birth control pills?", [("label_answer", {"brand": "zepbound"})], "label"),
    ("Is Wegovy approved to reduce cardiovascular risk?", [("label_answer", {"brand": "wegovy"})], "label"),
    ("How long can Trulicity pens stay at room temperature?", [("label_answer", {"brand": "trulicity"})], "label"),
    ("What do doctors say about cost and insurance in the visit notes?", [("visit_note_insights", {})], "notes"),
    ("Are reps hearing about needle fear from doctors?", [("visit_note_insights", {})], "notes"),
    ("Which Ohio endocrinologists should we prioritise, and what is Foundayo's boxed warning?",
     [("top_doctors", {"state": "OH", "specialty": "endocrinology"}), ("label_answer", {"brand": "foundayo"})], "two tools"),
    ("Compare the tirzepatide share of GLP-1 claims in Oregon and Utah.",
     [("market_summary", {"state": "OR"}), ("market_summary", {"state": "UT"})], "two tools"),
    ("What will the GLP-1 market share be in 2030?", [], "no tool"),
    ("What is the weather in Chicago today?", [], "no tool"),
]


def _norm(key, v):
    v = str(v).strip().lower()
    if key == "state":
        return (_state(v) or "").upper()
    if key in ("drug", "brand"):
        return BRAND_MOLECULE.get(v, v) if key == "drug" else v
    if key == "segment":
        return v[:1].upper()
    return v


def score_calls(steps: list[dict], expected: list) -> dict:
    """Tool choice: the set of tools called equals the expected set. Arguments: every expected argument matches
    (normalised: state names → codes, brands → molecules for FAERS) in some call to that tool."""
    called = [s["name"] for s in steps]
    tools_ok = sorted(set(called)) == sorted({t for t, _ in expected})
    args_ok = tools_ok
    for tool, exp in expected:
        got = [s["arguments"] for s in steps if s["name"] == tool]
        if not any(all(k in a and (_norm(k, a[k]) == _norm(k, v) if k != "specialty" else str(v) in str(a[k]).lower())
                       for k, v in exp.items()) for a in got):
            args_ok = False
    if len(expected) == 2 and expected[0][0] == expected[1][0]:        # same tool twice with different states
        states = {_norm("state", s["arguments"].get("state", "")) for s in steps if s["name"] == expected[0][0]}
        args_ok = tools_ok and states >= {e[1]["state"] for e in expected}
    return {"tools_ok": tools_ok, "args_ok": args_ok, "n_calls": len(steps),
            "errors": sum(s["result"].startswith("Error") for s in steps)}


def load() -> pd.DataFrame:
    return pd.read_json(OUT, lines=True) if OUT.exists() else pd.DataFrame()


def run() -> None:
    done = set(load()["question"]) if OUT.exists() else set()
    with OUT.open("a", encoding="utf-8") as f:
        for q, expected, kind in QUESTIONS:
            if q in done:
                continue
            t0 = time.time()
            r = A.ask(q)
            rec = {"question": q, "type": kind, "answer": r["answer"], "steps": r["steps"], "seconds": round(time.time() - t0, 1)}
            f.write(json.dumps(rec) + "\n"); f.flush()
            print(kind, rec["seconds"], "s |", q, "→", [s["name"] for s in r["steps"]], flush=True)
    print("ALL DONE", flush=True)


if __name__ == "__main__":
    run()
