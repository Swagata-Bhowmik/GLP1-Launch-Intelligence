import plotly.graph_objects as go
import streamlit as st

import aurora as A

A.setup("Doctor 360")
st.markdown("## Doctor 360")
st.caption("One row per doctor: prescribing, registry, payments, research and score, joined on NPI.")

t = A.load("targets")

q = st.text_input("Search by last name or 10-digit NPI", placeholder="e.g. Smith or 1003000126")
if not q:
    st.info("Type a name or NPI. Tip: the Targeting page lists top-ranked doctors to look up.")
    st.stop()

q = q.strip()
hits = t[t["npi"] == q] if q.isdigit() else t[t["last_name"].fillna("").str.upper() == q.upper()]
if hits.empty:
    st.warning("No doctor found. Only 2024 Part D prescribers of GLP-1 or diabetes drugs are included.")
    st.stop()

if len(hits) > 1:
    labels = {i: f"{r.first_name or ''} {r.last_name} · {r.specialty} · {r.city}, {r.state} · score {r.score}"
              for i, r in hits.head(200).iterrows()}
    pick = st.selectbox(f"{len(hits):,} doctors match; pick one", list(labels), format_func=labels.get)
    d = hits.loc[pick]
else:
    d = hits.iloc[0]

seg_color = A.SEGMENT_COLOR[d["segment"][0]]
st.html(f"""
<div class="aur-card" style="display:flex; gap:18px; align-items:center; border-top:4px solid {seg_color}">
  <div style="width:62px;height:62px;border-radius:50%;display:grid;place-items:center;font-weight:800;font-size:22px;
              color:#fff;background:linear-gradient(135deg,#7C5CFF,#22D3C5)">{(d['first_name'] or ' ')[0]}{(d['last_name'] or ' ')[0]}</div>
  <div style="flex:1">
    <div style="font-family:'Plus Jakarta Sans',sans-serif;font-size:22px;font-weight:800;color:#140F33">
      Dr. {str(d['first_name'] or '').title()} {str(d['last_name']).title()}</div>
    <div style="color:#6B6790">{d['specialty']} · {str(d['city']).title()}, {d['state']} {d['practice_zip5'] or ''} · NPI {d['npi']}</div>
    <div style="margin-top:6px"><span class="aur-pill" style="background:{seg_color}22;color:#140F33">{d['segment']}</span></div>
  </div>
  <div style="text-align:right">
    <div class="aur-label">Targeting score</div>
    <div class="aur-big">{d['score']:.1f}</div>
    <div class="aur-note">rank {d['rank']:,} of {len(t):,}</div>
  </div>
</div>
""")

A.kpis([
    {"label": "Diabetes claims (2024)", "value": int(d["diabetes_total_claims"]), "icon": "▤", "tint": "#E3FBF8"},
    {"label": "GLP-1 claims", "value": int(d["glp1_claims"]), "icon": "◉"},
    {"label": "GLP-1 % of diabetes Rx", "value": 100 * (d["glp1_share_of_diabetes"] or 0), "decimals": 0, "suffix": "%", "icon": "◐", "tint": "#EEF2FF"},
    {"label": "GLP-1 industry payments", "value": int(d["op_lilly_payments"] + d["op_novo_payments"]),
     "icon": "★", "tint": "#FFF6DD", "note": "Open Payments records 2024–2025, both manufacturers"},
])

c1, c2 = st.columns([1.1, 1])
with c1:
    comp = {k[2:].replace("_", " "): d[k] for k in t.columns if k.startswith("c_")}
    weights = {"potential": .30, "glp1 experience": .20, "headroom": .15, "tirzepatide openness": .15,
               "oral affinity": .10, "research": .05, "coverage gap": .05}
    names = list(comp)
    contrib = [100 * comp[n] * weights.get(n, 0) for n in names]
    fig = go.Figure(go.Bar(x=contrib, y=names, orientation="h", marker=dict(color=A.VIOLET, cornerradius=5),
                           text=[f"{c:.1f} pts" for c in contrib], textposition="outside", cliponaxis=False,
                           customdata=[comp[n] for n in names],
                           hovertemplate="<b>%{y}</b><br>component %{customdata:.2f} → %{x:.1f} points<extra></extra>"))
    fig.update_layout(title="Why this score: points from each component", height=360, yaxis_autorange="reversed",
                      xaxis_range=[0, 35], showlegend=False)
    st.plotly_chart(fig)
with c2:
    st.markdown("#### Evidence")
    reasons = d["reasons"] or "Below the top 20,000: open the components chart for the breakdown."
    for r in reasons.split(" · "):
        st.markdown(f"- {r}")
    extra = []
    if d.get("pubmed_papers", 0):
        extra.append(f"{int(d['pubmed_papers'])} linked GLP-1 papers")
    if d.get("trials", 0):
        extra.append(f"{int(d['trials'])} linked GLP-1 trials")
    if extra:
        st.markdown("- " + " · ".join(extra) + " *(name-matched: verify before use)*")
    A.callout("Pre-visit brief and visit-note analysis for this doctor arrive with the NLP + RAG phases (notebooks 09–15).")
