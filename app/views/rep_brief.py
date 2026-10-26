import pandas as pd
import streamlit as st

import aurora as A
from glp1_intel.rag.label_facts import key_facts

A.setup("Pre-visit brief")
st.markdown("## Pre-visit brief")
st.caption("Pick your territory and a doctor. The brief is built instantly from data and the FDA label: numbers by code, "
           "label sentences quoted exactly with their source. An AI-written version is optional.")
A.page_help("rep_brief")

t = A.load("targets")
BRANDS = ["Foundayo", "Mounjaro", "Zepbound", "Trulicity", "Ozempic", "Wegovy", "Rybelsus", "Victoza", "Saxenda"]
OBJ_TEXT = {"cost_coverage": "cost / insurance coverage", "gi_tolerability": "GI side effects", "elderly_frailty": "use in frail or older patients",
            "efficacy_vs_comp": "efficacy vs competitors", "injection_aversion": "injection / needle aversion",
            "supply_access": "supply and access", "safety_other": "other safety (pancreatitis, thyroid, eyes)"}

c1, c2, c3 = st.columns([1, 1.6, 1.2])
state = c1.selectbox("Territory (state)", sorted(t["state"].dropna().unique()), index=sorted(t["state"].dropna().unique()).index("OH"))
specs = t.loc[t["state"] == state, "specialty"].value_counts().index[:15].tolist()
spec = c2.selectbox("Specialty", ["All specialties"] + specs)
brand = c3.selectbox("Product to discuss", BRANDS)

v = t[t["state"] == state]
if spec != "All specialties":
    v = v[v["specialty"] == spec]
top = v.head(20).copy()
top["label"] = [f"#{r.rank:,} · Dr. {str(r.first_name or '').title()[:1]}. {str(r.last_name).title()} · {r.specialty} · {str(r.city).title()}"
                for r in top.itertuples()]
if top.empty:
    st.info("No doctors in this filter.")
    st.stop()
pick = st.selectbox("Doctor (top 20 by targeting score)", top["label"])
d = top[top["label"] == pick].iloc[0]

# ── Who and why (all from data) ─────────────────────────────────────────────
A.kpis([
    {"label": "Targeting rank", "value": int(d["rank"]), "note": f"score {d['score']:.1f} of 100", "icon": "★"},
    {"label": "Diabetes claims (Part D 2024)", "value": int(d["diabetes_total_claims"]), "icon": "▤", "tint": "#E3FBF8"},
    {"label": "GLP-1 claims", "value": int(d["glp1_claims"]), "note": f"{d['glp1_share_of_diabetes']:.0%} of diabetes Rx", "icon": "◉"},
    {"label": "Tirzepatide share", "value": 100 * float(d["tirzepatide_share"]), "suffix": "%", "icon": "◐", "tint": "#FFF6DD",
     "note": f"{int(d['rybelsus_claims']):,} oral semaglutide claims"},
])
with st.container(border=True):
    st.markdown(f"**Why this doctor:** {d['reasons']}  \n**Segment:** {d['segment']}")

# ── What the label says (verbatim) ──────────────────────────────────────────
st.markdown(f"#### What the {brand} label says")
facts = key_facts(brand.lower())
for f in facts:
    box = st.container(border=True)
    if f["fact"] == "Boxed warning":
        box.markdown("**⚠️ Boxed warning (always discuss, fair balance)**")
    else:
        box.markdown(f"**{f['fact']}**")
    box.markdown(f"> {f['text']}")
    box.caption(f"Source: {f['source']}")

# ── What similar doctors raise (synthetic visit notes) ──────────────────────
@st.cache_data
def notes() -> pd.DataFrame:
    from glp1_intel.rag import knowledge_base as K
    kb = K.build()
    n = kb[kb["source"] == "note"].copy()
    n["specialty"] = n["title"].str.split(" · ").str[0]
    return n


nn = notes()
peer = nn[nn["specialty"] == d["specialty"]]
scope = d["specialty"]
if len(peer) < 15:
    peer, scope = nn, "all specialties"
obj = peer["objections"].explode().dropna().value_counts()
st.markdown("#### What similar doctors raise")
st.caption(f"From {len(peer):,} synthetic visit notes ({scope}); notebook 09. Share of notes mentioning each concern.")
cols = st.columns(3)
for col, (k, n) in zip(cols, obj.head(3).items()):
    col.html(f'<div class="aur-card"><div class="aur-label">{OBJ_TEXT.get(k, k)}</div>'
             f'<div class="aur-big">{100 * n / len(peer):.0f}%</div><div class="aur-note">{n} of {len(peer)} notes</div></div>')
if "cost_coverage" in obj.head(3).index:
    A.callout("The label contains no price or coverage information: route cost questions to the market-access team, "
              "and the Medicare GLP-1 Bridge (from July 2026) where relevant.")

# ── Optional: AI-written brief ──────────────────────────────────────────────
st.markdown("#### Draft with AI (optional)")
st.caption("Uses the notebook-14 pipeline: code writes the profile, the boxed warning is added by metadata, and a small local "
           "LLM writes short cited parts. ~3–4 minutes on a laptop CPU; each part is checked for faithfulness.")
from glp1_intel.cloud import LIGHT
if LIGHT:
    st.info("Switched off on this free server (the local LLM needs ~6 GB of memory). Run the app on a laptop to try it.")
elif st.button("Write AI brief"):
    from glp1_intel.agent.tools import _retriever
    from glp1_intel.rag import generate as G
    row = {**d.to_dict(), "research_themes": None}
    with st.status("Writing the brief (6 small LLM calls)…") as status:
        b = G.pre_visit_brief(row, _retriever(), brand=brand.lower())
        status.update(label="Done", state="complete")
    st.markdown(G.brief_markdown(b, f"AI draft · {brand}"))
    checks = []
    for part, text, src in [("key facts", b["points"], b["points_sources"]), ("safety", b["safety"], b["safety_sources"])] + \
                           [(f"concern: {c}", r["answer"], r["sources"]) for c, r in zip(b["concerns"], b["replies"])]:
        f = G.faithfulness(text, src.reset_index(drop=True))
        checks.append({"part": part, "sentences supported": "refusal" if G.is_refusal(text) else f"{int(f['supported'].sum())}/{len(f)}"})
    st.dataframe(pd.DataFrame(checks), hide_index=True)
    A.callout("Draft only: a small model can still add or blur details. Check every sentence against the quoted label above.", "warn")

st.caption("Public + synthetic data only. Not medical advice; discuss only label-consistent information.")
