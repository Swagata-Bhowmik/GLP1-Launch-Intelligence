import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import aurora as A

A.setup("Targeting")
st.markdown("## Who to target for the 2026 opportunity")
st.caption("Transparent 0–100 score: potential 30% · GLP-1 experience 20% · headroom 15% · tirzepatide openness 15% · "
           "oral affinity 10% · research 5% · coverage gap 5%. Details in notebook 05.")

t = A.load("targets")

# ── Filters in one row ──────────────────────────────────────────────────────
f1, f2, f3, f4 = st.columns([1.2, 1.6, 1.6, 1])
states = f1.multiselect("State", sorted(t["state"].dropna().unique()), placeholder="All states")
specs = f2.multiselect("Specialty", t["specialty"].value_counts().index[:25].tolist(), placeholder="All specialties")
segs = f3.multiselect("Segment", sorted(t["segment"].unique()), placeholder="All segments")
gap_only = f4.toggle("No industry contact", help="Doctors with no payment from either GLP-1 manufacturer in Open Payments 2024–2025")
no_industry = lambda df: (df["op_lilly_payments"] == 0) & (df["op_novo_payments"] == 0)

v = t
if states:
    v = v[v["state"].isin(states)]
if specs:
    v = v[v["specialty"].isin(specs)]
if segs:
    v = v[v["segment"].isin(segs)]
if gap_only:
    v = v[no_industry(v)]

A.kpis([
    {"label": "Doctors in view", "value": len(v), "icon": "◉"},
    {"label": "Diabetes claims covered", "value": v["diabetes_total_claims"].sum() / 1e6, "decimals": 2, "suffix": "M",
     "icon": "▤", "tint": "#E3FBF8", "note": f"{100 * v['diabetes_total_claims'].sum() / t['diabetes_total_claims'].sum():.1f}% of all"},
    {"label": "Median score", "value": float(v["score"].median()) if len(v) else 0, "decimals": 1, "icon": "★", "tint": "#FFF6DD"},
    {"label": "No industry contact", "value": 100 * float(no_industry(v).mean()) if len(v) else 0,
     "decimals": 0, "suffix": "%", "icon": "◐", "tint": "#FFEDE6"},
])

# ── Ranked list ─────────────────────────────────────────────────────────────
n_show = st.select_slider("Rows to show", options=[25, 50, 100, 250, 500], value=50)
top = v.head(n_show).copy()
top["doctor"] = "Dr. " + top["first_name"].fillna("").str.title().str[:1] + ". " + top["last_name"].fillna("").str.title()
top["glp1_pct"] = 100 * top["glp1_share_of_diabetes"].fillna(0)
st.dataframe(
    top[["rank", "doctor", "specialty", "city", "state", "segment", "score", "glp1_claims", "glp1_pct", "reasons"]],
    hide_index=True, height=min(38 * (n_show + 1), 620),
    column_config={
        "rank": st.column_config.NumberColumn("#", width="small"),
        "doctor": st.column_config.TextColumn("Doctor"),
        "specialty": st.column_config.TextColumn("Specialty"),
        "city": st.column_config.TextColumn("City"),
        "state": st.column_config.TextColumn("State", width="small"),
        "segment": st.column_config.TextColumn("Segment"),
        "score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.1f"),
        "glp1_claims": st.column_config.NumberColumn("GLP-1 claims", format="%d"),
        "glp1_pct": st.column_config.NumberColumn("GLP-1 % of diabetes Rx", format="%.0f%%"),
        "reasons": st.column_config.TextColumn("Why", width="large"),
    })
st.download_button("Download this list (CSV)", v.head(5000).drop(columns=[c for c in v if c.startswith("c_")]).to_csv(index=False),
                   file_name="glp1_targets.csv", mime="text/csv")

# ── Segment mix + map of targets ────────────────────────────────────────────
c1, c2 = st.columns([1, 1.2])
with c1:
    seg = v.groupby("segment").size().reindex(sorted(t["segment"].unique()), fill_value=0)
    fig = go.Figure(go.Bar(x=seg.values, y=seg.index, orientation="h",
                           marker=dict(color=[A.SEGMENT_COLOR[s[0]] for s in seg.index], cornerradius=5),
                           text=[f"{n:,}" for n in seg.values], textposition="outside", cliponaxis=False,
                           hovertemplate="<b>%{y}</b><br>%{x:,} doctors<extra></extra>"))
    fig.update_layout(title="Segments in view", height=360, yaxis_autorange="reversed",
                      xaxis_range=[0, max(seg.max(), 1) * 1.25], showlegend=False)
    st.plotly_chart(fig)
with c2:
    top_n = v.head(5000).groupby("state").size().reset_index(name="targets")
    fig = px.choropleth(top_n, locations="state", locationmode="USA-states", scope="usa", color="targets",
                        color_continuous_scale=["#EFEAFF", "#B9A8FF", "#7C5CFF", "#3B2499"],   # one hue, light → dark
                        labels={"targets": "Doctors"}, hover_name="state", hover_data={"state": False})
    fig.update_layout(title="Where the top 5,000 (in view) practise", height=360,
                      geo=dict(bgcolor="rgba(0,0,0,0)", lakecolor="rgba(0,0,0,0)"),
                      coloraxis_colorbar=dict(title="", thickness=12, len=0.7))
    st.plotly_chart(fig, config={"scrollZoom": False})        # page scrolling must not zoom the map

A.callout("Targeting decides <b>who receives relevant, label-consistent information first</b>, never what a doctor should prescribe. "
          "Names come from public CMS data.")
