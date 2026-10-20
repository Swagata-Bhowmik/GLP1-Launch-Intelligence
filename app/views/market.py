import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import aurora as A

A.setup("Market")
st.markdown("## Market landscape")
st.caption("Medicare Part D 2024 · Medicaid SDUD to Q1 2026 · colour = molecule")

brands = A.load("brands")
states = A.load("states")
spec = A.load("specialties")
trend = A.load("medicaid_trend")
chg = A.load("medicaid_change")

# ── Row 1: brands + state map ───────────────────────────────────────────────
c1, c2 = st.columns([1, 1.25])
with c1:
    b = brands[brands["claims"] > 20_000].sort_values("claims")
    fig = go.Figure(go.Bar(
        x=b["claims"] / 1e6, y=b["brand"], orientation="h",
        marker=dict(color=[A.MOLECULE_COLOR.get(m, "#E0607E") for m in b["molecule"]], cornerradius=6),
        text=[f"{v / 1e6:.2f}M" for v in b["claims"]], textposition="outside", cliponaxis=False,
        customdata=b[["generic", "prescribers"]],
        hovertemplate="<b>%{y}</b> (%{customdata[0]})<br>%{x:.2f}M claims<br>%{customdata[1]:,} prescribers<extra></extra>"))
    fig.update_layout(title="Claims by brand", height=420, xaxis_title="Million claims", showlegend=False,
                      xaxis_range=[0, b["claims"].max() / 1e6 * 1.2])
    st.plotly_chart(fig)

with c2:
    fig = px.choropleth(states, locations="state", locationmode="USA-states", scope="usa", color="tirz_share",
                        # Diverging around the US average: teal = below, grey = average, violet = above
                        color_continuous_scale=["#0EA5A0", "#9FDCD8", "#EEEDF3", "#B9A8FF", "#5B3FE0"],
                        color_continuous_midpoint=30.1, range_color=(15, 45.2), hover_name="state",
                        hover_data={"state": False, "tirz_share": ":.1f", "glp1_claims": ":,", "prescribers": ":,"},
                        labels={"tirz_share": "Tirzepatide share %", "glp1_claims": "GLP-1 claims", "prescribers": "Prescribers"})
    fig.update_layout(title="Tirzepatide share vs semaglutide by state (US average 30%)", height=420,
                      geo=dict(bgcolor="rgba(0,0,0,0)", lakecolor="rgba(0,0,0,0)"),
                      coloraxis_colorbar=dict(title="%", thickness=12, len=0.7))
    st.plotly_chart(fig, config={"scrollZoom": False})        # page scrolling must not zoom the map

# ── Row 2: Medicaid trend ───────────────────────────────────────────────────
st.markdown("#### What is changing now: Medicaid prescriptions to Q1 2026")
fig = go.Figure()
for brand, mol, dash in [("Ozempic", "semaglutide", "solid"), ("Mounjaro", "tirzepatide", "solid"),
                         ("Trulicity", "dulaglutide", "solid"), ("Zepbound", "tirzepatide", "dash"), ("Wegovy", "semaglutide", "dash")]:
    d = trend[trend["brand"] == brand].sort_values("period")
    fig.add_trace(go.Scatter(x=d["period"], y=d["rx"] / 1e3, name=brand + (" (obesity)" if dash == "dash" else ""),
                             mode="lines+markers", line=dict(color=A.MOLECULE_COLOR[mol], width=3, dash=dash),
                             marker=dict(size=7), hovertemplate=f"<b>{brand}</b><br>%{{x}}: %{{y:,.0f}}k Rx<extra></extra>"))
fig.add_vrect(x0="2025 Q4", x1="2026 Q1", fillcolor="#FFEDE6", opacity=0.7, line_width=0,
              annotation_text="Jan 2026: CA, PA, NH, SC end obesity coverage", annotation_position="top left",
              annotation_font=dict(color="#B4472A", size=12))
fig.update_layout(height=430, yaxis_title="Prescriptions (thousands)", hovermode="x unified")
st.plotly_chart(fig)

c3, c4 = st.columns(2)
with c3:
    d = chg[chg["q4_2025"] > 3000].sort_values("pct")
    fig = go.Figure(go.Bar(
        x=d["pct"].clip(upper=100), y=d["state"], orientation="h",
        marker=dict(color=[A.PEACH if e else "#C9C3E6" for e in d["ended_coverage"]], cornerradius=4),
        text=[f"{p:+.0f}%" for p in d["pct"]], textposition="outside", cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>%{text} (Q4 2025 → Q1 2026)<extra></extra>"))
    fig.update_layout(title="Zepbound + Wegovy change, Q4 2025 → Q1 2026", height=560, xaxis_range=[-120, 125],
                      xaxis_ticksuffix="%", showlegend=False)
    st.plotly_chart(fig)
    A.callout("Orange = state ended Medicaid coverage of GLP-1s for weight loss on 1 Jan 2026. "
              "Those four states account for more than the entire national drop.", "warn")
with c4:
    s = spec.head(8).sort_values("glp1_claims")
    fig = go.Figure(go.Bar(
        x=s["glp1_claims"] / 1e6, y=s["specialty"], orientation="h", marker=dict(color="#C9C3E6", cornerradius=6),
        text=[f"{v / 1e6:.1f}M · tirz {t:.0f}% · {a:.0f}% adopt" for v, t, a in zip(s["glp1_claims"], s["tirz_share"], s["pct_adopting"])],
        textposition="outside", cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>%{x:.2f}M GLP-1 claims<extra></extra>"))
    fig.update_layout(title="GLP-1 claims by specialty", height=560, xaxis_range=[0, s["glp1_claims"].max() / 1e6 * 1.9],
                      xaxis_title="Million claims", showlegend=False)
    st.plotly_chart(fig)
    A.callout("Primary care writes ~75% of GLP-1 claims; endocrinologists prescribe the most per doctor and lead on tirzepatide.")
