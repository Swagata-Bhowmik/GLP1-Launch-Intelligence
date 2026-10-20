import plotly.graph_objects as go
import streamlit as st

import aurora as A

A.setup("Safety signals")
st.markdown("## Safety signals (FAERS)")
st.caption("FDA Adverse Event Reporting System, aggregated by openFDA · reports received to mid-2026")
A.callout("FAERS counts reflect <b>reporting</b>, not how often side effects happen: reports are voluntary and unverified, "
          "and there is no denominator. Use this to anticipate <b>what doctors may ask about</b>, never to compare drug safety.",
          "warn")

f = A.load("faers")
DRUGS = ["tirzepatide", "semaglutide", "dulaglutide", "liraglutide", "orforglipron"]
COLOR = {**A.MOLECULE_COLOR, "orforglipron": A.MOLECULE_COLOR["other"]}

picked = st.segmented_control("Molecules", DRUGS, selection_mode="multi", default=["tirzepatide", "semaglutide", "orforglipron"])
picked = picked or DRUGS[:2]

q = f[f["count_type"] == "reports_per_quarter"].pivot(index="term", columns="drug", values="count").loc["2023Q1":]
fig = go.Figure()
for d in picked:
    fig.add_trace(go.Scatter(x=q.index, y=q[d], name=d.title(), mode="lines+markers",
                             line=dict(color=COLOR[d], width=3), marker=dict(size=7),
                             hovertemplate=f"<b>{d.title()}</b><br>%{{x}}: %{{y:,}} reports<extra></extra>"))
fig.update_layout(title="Reports received per quarter", height=400, hovermode="x unified")
st.plotly_chart(fig)

st.markdown("#### Most-reported reactions")
cols = st.columns(len(picked))
for col, d in zip(cols, picked):
    r = f[(f["drug"] == d) & (f["count_type"] == "reactions")].nlargest(10, "count").sort_values("count")
    fig = go.Figure(go.Bar(x=r["count"], y=r["term"].str.capitalize(), orientation="h",
                           marker=dict(color=COLOR[d], cornerradius=4),
                           hovertemplate="<b>%{y}</b><br>%{x:,} reports<extra></extra>"))
    fig.update_layout(title=d.title(), height=420, showlegend=False, margin=dict(l=0, r=10, t=40, b=10))
    col.plotly_chart(fig)
