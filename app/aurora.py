"""Aurora theme for the Streamlit app: global CSS, animated hero, KPI cards, Plotly template, data loaders.

Palette (approved 18 Oct 2026, preview: docs/architecture/theme_preview.html)
    ink #140F33 · violet #7C5CFF · aqua #22D3C5 · peach #FF8A65 (alerts only) · amber #FFC857 · mist #F6F4FF
Chart colours follow the molecule everywhere (same as the notebooks): tirzepatide violet, semaglutide teal,
dulaglutide amber, liraglutide blue.
"""
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

DATA = Path(__file__).parent / "data"

INK, VIOLET, AQUA, PEACH, AMBER, MIST = "#140F33", "#7C5CFF", "#22D3C5", "#FF8A65", "#FFC857", "#F6F4FF"
TEXT, TEXT_2, GRID = "#1E1B3A", "#6B6790", "#ECE8FA"
MOLECULE_COLOR = {"tirzepatide": "#7C5CFF", "semaglutide": "#0EA5A0", "dulaglutide": "#E8A33D",
                  "liraglutide": "#3B82F6", "other": "#E0607E"}
SEGMENT_COLOR = {"A": "#2a78d6", "B": "#eb6834", "C": "#1baf7a", "D": "#eda100", "E": "#e87ba4", "F": "#C9C3E6"}

# ── Plotly template: quiet grid, Aurora fonts, direct labels preferred ──────
pio.templates["aurora"] = go.layout.Template(layout=go.Layout(
    font=dict(family="Inter, Segoe UI, sans-serif", size=13, color=TEXT),
    title=dict(font=dict(family="Plus Jakarta Sans, Inter, sans-serif", size=17, color=INK), x=0, xanchor="left"),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    xaxis=dict(gridcolor=GRID, zeroline=False, linecolor=GRID, tickfont=dict(color=TEXT_2)),
    yaxis=dict(gridcolor=GRID, zeroline=False, linecolor=GRID, tickfont=dict(color=TEXT_2)),
    hoverlabel=dict(bgcolor="white", bordercolor=VIOLET, font=dict(color=TEXT, size=13)),
    margin=dict(l=10, r=20, t=50, b=10), legend=dict(orientation="h", y=-0.15, font=dict(color=TEXT_2)),
    colorway=list(MOLECULE_COLOR.values()),
))
pio.templates.default = "aurora"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@600;700;800&family=Inter:wght@400;500;600&display=swap');
html, body, [class*="css"], .stMarkdown, .stText { font-family: 'Inter', 'Segoe UI', sans-serif; }
h1, h2, h3 { font-family: 'Plus Jakarta Sans', 'Inter', sans-serif !important; letter-spacing: -.02em; color: #140F33; }
.block-container { padding-top: 4.2rem; max-width: 1240px; }
[data-testid="stHeader"] { background: transparent; }

/* Sidebar: midnight ink with soft glow */
[data-testid="stSidebar"] { background: radial-gradient(120% 60% at 0% 0%, #2B1F6B 0%, #140F33 55%); }
[data-testid="stSidebar"] * { color: #E9E5FF !important; }
[data-testid="stSidebarNav"] a[aria-current="page"] { background: rgba(124,92,255,.28); border-radius: 10px; }
[data-testid="stSidebarNav"] a:hover { background: rgba(255,255,255,.08); border-radius: 10px; }

/* Cards */
.aur-card { background: #fff; border: 1px solid #E7E3F7; border-radius: 18px; padding: 18px 20px;
            box-shadow: 0 10px 30px -14px rgba(76,52,190,.28); transition: transform .25s, box-shadow .25s;
            animation: aurRise .6s cubic-bezier(.2,.7,.2,1) both; }
.aur-card:hover { transform: translateY(-3px); box-shadow: 0 18px 40px -16px rgba(76,52,190,.38); }
@keyframes aurRise { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: none; } }
.aur-label { color: #6B6790; font-size: 13px; }
.aur-big { font-family: 'Plus Jakarta Sans', sans-serif; font-size: 30px; font-weight: 800; color: #140F33; margin: 4px 0 2px; }
.aur-note { color: #0E9F94; font-size: 12.5px; font-weight: 600; }
.aur-pill { display: inline-block; padding: 3px 10px; border-radius: 99px; font-size: 12px; font-weight: 600; }
.aur-callout { border-left: 5px solid #7C5CFF; background: #F3EEFF; color: #2A1B5C; padding: 12px 16px; border-radius: 0 12px 12px 0; }
.aur-warn { border-left: 5px solid #FF8A65; background: #FFF0EA; color: #7A2E17; padding: 12px 16px; border-radius: 0 12px 12px 0; }

/* Buttons and widgets pick up the violet accent */
.stButton > button, .stDownloadButton > button { border-radius: 12px; border: 0; color: #fff !important;
    background: linear-gradient(120deg, #7C5CFF, #5B8CFF 55%, #22D3C5); background-size: 160% auto; transition: background-position .4s; }
.stButton > button:hover, .stDownloadButton > button:hover { background-position: right center; }
@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }
</style>
"""


def setup(title: str) -> None:
    """Call first on every page: tab title, wide layout is set in app.py; inject CSS."""
    st.html(CSS)


def hero(title: str, highlight: str, subtitle: str, eyebrow: str = "Live · public US data") -> None:
    """Animated aurora banner (drifting colour blobs + shimmering gradient text)."""
    st.html(f"""
    <div class="aur-hero">
      <div class="blob b1"></div><div class="blob b2"></div><div class="blob b3"></div>
      <span class="eyebrow"><span class="dot"></span>{eyebrow}</span>
      <h1>{title} <span class="grad">{highlight}</span></h1>
      <p>{subtitle}</p>
    </div>
    <style>
      .aur-hero {{ position: relative; overflow: hidden; background: #140F33; color: #fff; border-radius: 24px;
                   padding: 30px 32px 34px; margin-bottom: 6px; }}
      .aur-hero .blob {{ position: absolute; border-radius: 50%; filter: blur(55px); opacity: .55; animation: drift 16s ease-in-out infinite alternate; }}
      .aur-hero .b1 {{ width: 340px; height: 340px; background: #7C5CFF; top: -150px; left: -60px; }}
      .aur-hero .b2 {{ width: 300px; height: 300px; background: #22D3C5; bottom: -180px; right: 12%; animation-delay: -5s; }}
      .aur-hero .b3 {{ width: 220px; height: 220px; background: #FF8A65; top: -40px; right: -60px; opacity: .35; animation-delay: -9s; }}
      @keyframes drift {{ to {{ transform: translate(50px, 30px) scale(1.15); }} }}
      .aur-hero > :not(.blob) {{ position: relative; }}
      .aur-hero .eyebrow {{ display: inline-flex; gap: 8px; align-items: center; font-size: 12px; letter-spacing: .12em; text-transform: uppercase;
                            background: rgba(255,255,255,.1); border: 1px solid rgba(255,255,255,.18); padding: 5px 12px; border-radius: 99px; }}
      .aur-hero .dot {{ width: 8px; height: 8px; border-radius: 50%; background: #22D3C5; animation: pulse 2s infinite; }}
      @keyframes pulse {{ 0% {{ box-shadow: 0 0 0 0 rgba(34,211,197,.7); }} 70% {{ box-shadow: 0 0 0 10px rgba(34,211,197,0); }} 100% {{ box-shadow: 0 0 0 0 rgba(34,211,197,0); }} }}
      .aur-hero h1 {{ font-family: 'Plus Jakarta Sans', sans-serif; font-size: clamp(26px, 4vw, 40px); font-weight: 800; margin: 14px 0 6px;
                      color: #fff !important; line-height: 1.1; letter-spacing: -.02em; }}
      .aur-hero .grad {{ background: linear-gradient(90deg, #B9A8FF, #7FE9DF, #B9A8FF); background-size: 200% auto;
                         -webkit-background-clip: text; background-clip: text; color: transparent; animation: shine 6s linear infinite; }}
      @keyframes shine {{ to {{ background-position: 200% center; }} }}
      .aur-hero p {{ color: #CFC9F2; margin: 0; max-width: 760px; font-size: 15.5px; }}
    </style>
    """)


def kpis(items: list[dict]) -> None:
    """Row of KPI cards with count-up numbers. items: {label, value, suffix?, decimals?, note?, icon?, tint?}."""
    cards = []
    for i, k in enumerate(items):
        cards.append(f"""
        <div class="aur-card kpi" style="animation-delay:{0.06 * i:.2f}s">
          <div class="aur-label"><span class="ic" style="background:{k.get('tint', '#EFEAFF')}">{k.get('icon', '◉')}</span>{k['label']}</div>
          <div class="aur-big" data-count="{k['value']}" data-dec="{k.get('decimals', 0)}" data-suffix="{k.get('suffix', '')}">0</div>
          <div class="aur-note">{k.get('note', '')}</div>
        </div>""")
    st.html(f"""
    <div class="kpi-row">{''.join(cards)}</div>
    <style>
      .kpi-row {{ display: grid; gap: 14px; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); margin: 8px 0 4px; }}
      .kpi {{ position: relative; overflow: hidden; }}
      .kpi::before {{ content: ""; position: absolute; inset: 0 0 auto 0; height: 4px; background: linear-gradient(120deg, #7C5CFF, #5B8CFF 45%, #22D3C5); }}
      .kpi .ic {{ display: inline-grid; place-items: center; width: 26px; height: 26px; border-radius: 9px; margin-right: 8px; font-size: 13px; color: #4B32C8; }}
    </style>
    <script>
      document.querySelectorAll('[data-count]').forEach(el => {{
        if (el.dataset.done) return; el.dataset.done = 1;
        const target = parseFloat(el.dataset.count), dec = +el.dataset.dec, suf = el.dataset.suffix, t0 = performance.now();
        (function tick(now) {{
          const p = Math.min((now - t0) / 1300, 1), e = 1 - Math.pow(1 - p, 3);
          el.textContent = (target * e).toLocaleString('en-US', {{minimumFractionDigits: dec, maximumFractionDigits: dec}}) + suf;
          if (p < 1) requestAnimationFrame(tick);
        }})(t0);
      }});
    </script>
    """, unsafe_allow_javascript=True)


def callout(text: str, kind: str = "info") -> None:
    st.html(f'<div class="{"aur-warn" if kind == "warn" else "aur-callout"}">{text}</div>')


@st.cache_data
def load(name: str) -> pd.DataFrame:
    return pd.read_parquet(DATA / f"{name}.parquet")


@st.cache_data
def load_kpis() -> dict:
    return json.loads((DATA / "kpis.json").read_text())
