from pathlib import Path

import streamlit as st

import aurora as A
import guide_content as G

FIGURES = Path(__file__).resolve().parents[2] / "reports" / "figures"

A.setup("Notebooks")
st.markdown("## The notebooks behind the website")
st.caption("A learning ladder: data → NLP basics → transformers → retrieval → RAG → agents → evaluation. "
           "Each notebook teaches the theory in plain language, applies it, and saves what the next one needs.")
A.callout("<b>How to read this page:</b> each card says why the notebook exists, what it did, its key result, the decision it led to, "
          "and which website page uses it. Open a card for its main chart and links to the full notebook "
          "(<b>nbviewer</b> shows it with all outputs; <b>GitHub</b> shows the file).")

stages = list(dict.fromkeys(nb["stage"] for nb in G.NOTEBOOKS))
pick = st.segmented_control("Show", ["All"] + stages, default="All")
for nb in G.NOTEBOOKS:
    if pick not in (None, "All") and nb["stage"] != pick:
        continue
    with st.expander(f"**{nb['n']} · {nb['title']}**  ·  {nb['stage']}", expanded=nb["n"] in ("05", "12", "14")):
        left, right = st.columns([1.15, 1])
        with left:
            st.markdown(f"**Why:** {nb['why']}")
            st.markdown(f"**What was done:** {nb['did']}")
            st.markdown(f"**Key result:** {nb['result']}")
            st.markdown(f"**Decision:** {nb['decision']}")
            st.markdown(f"**Used on the website:** {nb['page']}")
            if nb["file"]:
                b1, b2 = st.columns(2)
                b1.link_button("Open with outputs (nbviewer)", G.NBVIEWER + nb["file"], icon=":material/visibility:", width="stretch")
                b2.link_button("Open on GitHub", G.GITHUB_NB + nb["file"], icon=":material/code:", width="stretch")
        with right:
            if nb["figure"] and (FIGURES / nb["figure"]).exists():
                st.image(str(FIGURES / nb["figure"]), caption=f"From notebook {nb['n']}")
