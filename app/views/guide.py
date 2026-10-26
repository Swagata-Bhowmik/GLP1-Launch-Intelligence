import streamlit as st

import aurora as A
import guide_content as G

A.setup("Start here")
A.hero("Start here:", "the project guide",
       "What LaunchLens is, how to read this website, where to find each answer, and what every term means. "
       "Five minutes here makes every other page easy to follow.", eyebrow="Guide · for reviewers")

st.markdown("#### The project in one line")
A.callout(G.SUMMARY["one_line"])

c1, c2 = st.columns(2)
with c1:
    st.markdown("##### The problem")
    st.markdown(G.SUMMARY["problem"])
    st.markdown("##### Who it is for")
    st.markdown(G.SUMMARY["users"])
with c2:
    st.markdown("##### What was built")
    st.markdown(G.SUMMARY["solution"])
    st.markdown("##### What is new, and what is not")
    st.markdown(G.SUMMARY["novelty"])

st.markdown("#### A 5-minute tour: open the pages in this order")
st.caption("Every page also has a “This page answers” box at the top, and a “How to read this page” panel that explains each chart.")
cols = st.columns(3)
for i, (title, path, text) in enumerate(G.TOUR):
    with cols[i % 3]:
        with st.container(border=True):
            st.markdown(f"**{i + 1}. {title}**")
            st.caption(text)
            if path:
                st.page_link(f"views/{path}.py", label=f"Open {title}", icon=":material/arrow_forward:")
            else:
                st.page_link("views/landing.py", label="Open Home", icon=":material/arrow_forward:")

st.markdown("#### Where to find what")
st.dataframe({"If you want to know…": [w[0] for w in G.WHERE], "Go to": [w[1] for w in G.WHERE],
              "Built in notebook": [w[2] for w in G.WHERE]}, hide_index=True, width="stretch")

st.markdown("#### Words used on this site")
g1, g2 = st.columns(2)
half = (len(G.GLOSSARY) + 1) // 2
for col, items in ((g1, G.GLOSSARY[:half]), (g2, G.GLOSSARY[half:])):
    with col:
        for term, meaning in items:
            st.markdown(f"**{term}:** {meaning}")

st.markdown("#### Everything else")
l1, l2, l3, l4 = st.columns(4)
l1.link_button("Code on GitHub", G.REPO, icon=":material/code:", width="stretch")
l2.link_button("Models & data on Hugging Face", G.HF, icon=":material/deployed_code:", width="stretch")
l3.page_link("views/notebooks.py", label="All notebooks", icon=":material/menu_book:")
l4.page_link("views/decisions.py", label="Decisions & results", icon=":material/fact_check:")
A.callout("Independent portfolio project on public and synthetic data. Not affiliated with any pharmaceutical company. "
          "Not medical advice. Live AI-writing features are switched off on this free server (they need about 6 GB of memory); "
          "their evaluated outputs are shown instead.")
