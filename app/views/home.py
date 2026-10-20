import streamlit as st

import aurora as A

A.setup("Overview")
k = A.load_kpis()

A.hero("GLP-1", "Launch Intelligence",
       "Which doctors to prioritise after the 2026 GLP-1 market shift (oral Foundayo approval in April, "
       "Medicare GLP-1 Bridge from July), and why. Built on real public US data.")

A.kpis([
    {"label": "GLP-1 prescribers", "value": k["prescribers"], "note": "Medicare Part D 2024", "icon": "◉"},
    {"label": "GLP-1 claims", "value": k["glp1_claims"] / 1e6, "decimals": 1, "suffix": "M",
     "note": f"US${k['glp1_cost_bn']} bn gross spend", "icon": "▤", "tint": "#E3FBF8"},
    {"label": "Tirzepatide share", "value": k["tirz_share"], "decimals": 1, "suffix": "%",
     "note": "vs semaglutide, 2024", "icon": "◐", "tint": "#EEF2FF"},
    {"label": "Ready doctors without Lilly contact", "value": k["ready_no_lilly_pct"], "decimals": 0, "suffix": "%",
     "note": f"{k['ready_novo_not_lilly_pct']:.0f}% engaged by Novo only", "icon": "★", "tint": "#FFF6DD"},
])

st.markdown("#### Three things the data says")
c1, c2, c3 = st.columns(3)
insights = [
    ("Coverage decides volume", "#FF8A65",
     "Medicaid obesity GLP-1s grew 27× in two years, then fell 40–50% in one quarter when four states ended coverage "
     "(Jan 2026). The Medicare Bridge pulls the same lever the other way."),
    ("Share swings 2.5× by state", "#7C5CFF",
     "Tirzepatide holds ~18% of the tirzepatide + semaglutide market in Oregon and California but ~45% in Utah and Louisiana. "
     "Local factors, not the molecule, explain the gap."),
    ("High-value doctors are under-reached", "#22D3C5",
     f"A third of the 10,000 most Bridge-ready doctors had no Lilly payment record in 2024–25, and "
     f"{k['ready_novo_not_lilly_pct']:.0f}% were engaged by Novo only."),
]
for col, (title, color, body) in zip((c1, c2, c3), insights):
    col.html(f"""<div class="aur-card" style="border-top:4px solid {color}; min-height: 190px">
                 <div style="font-family:'Plus Jakarta Sans',sans-serif;font-weight:700;font-size:17px;color:#140F33;margin-bottom:6px">{title}</div>
                 <div style="color:#4A4570;font-size:14.5px;line-height:1.55">{body}</div></div>""")

st.markdown("#### Explore")
n1, n2, n3, n4 = st.columns(4)
n1.page_link("views/market.py", label="Market landscape", icon=":material/bar_chart:")
n2.page_link("views/targeting.py", label="Who to target", icon=":material/target:")
n3.page_link("views/doctor.py", label="Doctor 360 lookup", icon=":material/person_search:")
n4.page_link("views/safety.py", label="Safety signals", icon=":material/health_and_safety:")

A.callout("<b>How to read this:</b> prescribing is Medicare Part D 2024 (the latest doctor-level data CMS publishes); "
          "trends to Q1 2026 come from Medicaid; payments from Open Payments 2024–25. The 2026 opportunity is "
          "<b>modelled</b>, not observed.")
