import json

import pandas as pd
import streamlit as st

import aurora as A
from glp1_intel.nlp.classical import EVAL_DIR

A.setup("Ask AI")
A.hero("Ask AI:", "answers you can trace",
       "A small open LLM chooses among five data tools. Every number comes from code, label answers come with citations, "
       "and warnings from the safety checks are attached automatically.", eyebrow="Agent · RAG · guardrails")

GRADE_STYLE = {"correct": ("#E3F8F5", "#0E7C72"), "partial": ("#FFF6E0", "#8A5A00"), "wrong": ("#FFECE6", "#A63A1A")}
TOOL_LABEL = {"top_doctors": "Doctor ranking · Medicare Part D 2024", "market_summary": "Market summary · Medicare Part D 2024",
              "side_effect_reports": "Side-effect reports · FDA FAERS", "label_answer": "FDA label · retrieval + guard",
              "visit_note_insights": "Visit notes · semantic search"}


@st.cache_data
def examples() -> pd.DataFrame:
    runs = pd.read_json(EVAL_DIR / "nb15_agent.jsonl", lines=True)
    grades = pd.read_csv(EVAL_DIR / "nb15_manual_grades.csv")
    return runs.merge(grades[["question", "grade", "note"]], on="question")


def show_answer(answer: str, steps: list[dict]) -> None:
    from glp1_intel.agent.agent import finalize
    text = finalize(answer, steps)
    body, _, used = text.rpartition("\n\n— ")
    if body.startswith("⚠️"):
        warn, _, body = body.partition("\n\n")
        A.callout(warn, "warn")
    with st.container(border=True):
        st.markdown(body)
        st.caption("— " + used)


def show_steps(steps: list[dict]) -> None:
    if not steps:
        st.caption("No tool was called: the model answered without data (treat with care).")
    for i, s in enumerate(steps, 1):
        st.markdown(f"**Step {i} · {TOOL_LABEL.get(s['name'], s['name'])}**")
        st.code(f"{s['name']}({json.dumps(s['arguments'])})", language="python")
        st.text(s["result"][:1500])


tab_ex, tab_live = st.tabs(["Example questions (instant)", "Ask your own (live)"])

with tab_ex:
    ex = examples()
    counts = ex["grade"].value_counts()
    A.callout(f"These 21 questions were run once and <b>graded by hand</b> (notebook 15): "
              f"<b>{counts.get('correct', 0)} correct</b>, {counts.get('partial', 0)} partial, {counts.get('wrong', 0)} wrong. "
              "The grade and the reason are shown with each answer, so you can see where a small model still fails.")
    q = st.selectbox("Pick a question", ex["question"], index=0)
    r = ex[ex["question"] == q].iloc[0]
    bg, fg = GRADE_STYLE[r["grade"]]
    st.html(f'<span class="aur-pill" style="background:{bg};color:{fg}">Hand grade: {r["grade"]}</span>'
            + (f' <span style="color:#6B6790;font-size:13px">· {r["note"]}</span>' if isinstance(r["note"], str) and r["note"] else ""))
    show_answer(r["answer"], r["steps"])
    with st.expander(f"How the agent got there · {len(r['steps'])} tool call(s) · {r['seconds']:.0f} s on a laptop CPU"):
        show_steps(r["steps"])

with tab_live:
    A.callout("Runs the real agent: <b>Qwen2.5-1.5B-Instruct</b> on this machine's CPU, about <b>1–3 minutes</b> per question "
              "(the first question also loads the model). Try things like <i>“Top cardiologists in Texas”</i>, "
              "<i>“Tirzepatide share in Utah”</i> or <i>“Does Foundayo interact with simvastatin?”</i>", "info")
    question = st.text_input("Your question", placeholder="e.g. Which endocrinologists in Ohio should we prioritise?")
    if st.button("Ask", type="primary", disabled=not question.strip()):
        from glp1_intel.agent.agent import ask
        with st.status("Thinking: choosing a tool, running it, writing the answer…", expanded=False) as status:
            res = ask(question.strip())
            status.update(label=f"Done · {len(res['steps'])} tool call(s)", state="complete")
        show_answer(res["answer"], res["steps"])
        with st.expander("How the agent got there"):
            show_steps(res["steps"])

st.caption("Public + synthetic data only. Doctor names are never shown. Not medical advice; label answers must be checked "
           "against the full prescribing information before any use with health-care professionals.")
