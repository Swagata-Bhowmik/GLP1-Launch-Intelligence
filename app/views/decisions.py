from pathlib import Path

import streamlit as st

import aurora as A
import guide_content as G

FIGURES = Path(__file__).resolve().parents[2] / "reports" / "figures"
STATUS_STYLE = {"Met": ("#E3F8F5", "#0E7C72"), "Partly": ("#FFF6E0", "#8A5A00"), "Met (dose weak)": ("#E3F8F5", "#0E7C72"),
                "Not met": ("#FFECE6", "#A63A1A"), "Gap found": ("#FFECE6", "#A63A1A"), "Not done": ("#EEEDF3", "#4A4570")}

A.setup("Decisions & results")
st.markdown("## Decisions, results and limitations")
st.caption("What was chosen and why, what was achieved against each goal, and what is still weak. Details: notebook 17 and the README.")

tab_r, tab_d, tab_l = st.tabs(["Targets vs results", "Design decisions", "Limitations"])

with tab_r:
    A.callout("<b>How to read this:</b> each row is a goal, the measured result, and whether it was met. Brackets are 95% intervals: "
              "the range the score would likely fall in on a new test set of the same size. Failures are listed, not hidden.")
    rows = []
    for goal, result, status in G.RESULTS:
        bg, fg = STATUS_STYLE[status]
        rows.append(f"<tr><td>{goal}</td><td>{result}</td>"
                    f'<td><span class="aur-pill" style="background:{bg};color:{fg}">{status}</span></td></tr>')
    st.html(f"""<div class="aur-card" style="padding:6px 10px"><table class="ll-t">
      <tr><th>Goal</th><th>Result</th><th>Status</th></tr>{''.join(rows)}</table></div>
      <style>.ll-t {{ width:100%; border-collapse:collapse; font-size:14.5px; color:#1E2547 }}
      .ll-t th {{ text-align:left; color:#5A6386; font-weight:600; padding:10px 8px; border-bottom:1px solid #E4E8F5 }}
      .ll-t td {{ padding:10px 8px; border-bottom:1px solid #EEF1F8; vertical-align:top }}</style>""")
    f = FIGURES / "17_1_scorecard_intervals.png"
    if f.exists():
        st.image(str(f), caption="Every result with its 95% interval (notebook 17). Large test sets give tight intervals; "
                                 "the small hand-graded LLM tests are the least certain.")

with tab_d:
    A.callout("<b>How to read this:</b> each card is one design choice, the alternatives considered, and the reason. "
              "The notebook number shows where the choice was made and tested.")
    for i, (decision, alternatives, why, where) in enumerate(G.DECISIONS, 1):
        with st.container(border=True):
            st.markdown(f"**{i}. {decision}**  ·  notebook {where}")
            st.markdown(f"*Instead of:* {alternatives}  \n*Why:* {why}")

with tab_l:
    A.callout("Known weaknesses, stated openly. Each would be the next thing to improve.", "warn")
    for item in G.LIMITATIONS:
        st.markdown(f"- {item}")
    f = FIGURES / "17_2_targeting_representation.png"
    if f.exists():
        st.image(str(f), caption="Fairness check (notebook 17): the score favours endocrinologists (1.57×) and "
                                 "under-weights nurse practitioners (0.69×).")
