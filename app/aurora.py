"""LaunchLens theme for the Streamlit app: global CSS, hero banner, KPI cards, glowing cursor, Plotly template, loaders.

Look (Oct 2026 redesign, matches the landing site in site/): light sky-blue gradient, frosted-glass cards, deep-blue
glass sidebar, teal → blue gradients, Plus Jakarta Sans headings + Inter text, glowing cursor with a light trail.
Chart colours follow the molecule everywhere (same as the notebooks): tirzepatide violet, semaglutide teal,
dulaglutide amber, liraglutide blue.
"""
import base64
import json
from functools import lru_cache
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

DATA = Path(__file__).parent / "data"
STATIC = Path(__file__).parent / "static" / "site" / "assets"
SITE_URL = "https://swagata-bhowmik.github.io/GLP1-Launch-Intelligence/"

INK, VIOLET, AQUA, PEACH, AMBER, MIST = "#0B1030", "#7C5CFF", "#22D3C5", "#FF8A65", "#FFC857", "#F4F8FF"
TEAL, BLUE = "#14B8A6", "#4F6BFF"
TEXT, TEXT_2, GRID = "#1E2547", "#5A6386", "#E3EAF8"
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
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Inter:wght@400;500;600&display=swap');
html, body, [class*="css"], .stMarkdown, .stText { font-family: 'Inter', 'Segoe UI', sans-serif; }
h1, h2, h3, h4 { font-family: 'Plus Jakarta Sans', 'Inter', sans-serif !important; letter-spacing: -.025em; color: #0B1030; }
h2 { font-weight: 800 !important; }

/* Page: light sky gradient, same as the landing site */
[data-testid="stAppViewContainer"], [data-testid="stApp"] {
  background:
    radial-gradient(1100px 650px at 90% 0%, #DCEBFF 0%, transparent 60%),
    radial-gradient(800px 560px at 0% 35%, #E3FBF8 0%, transparent 55%),
    radial-gradient(900px 650px at 100% 80%, #EEE9FF 0%, transparent 55%),
    linear-gradient(180deg, #F4F8FF 0%, #EEF4FF 100%) !important; }
.block-container { padding-top: 3.6rem; max-width: 1280px; }
/* Top menu: frosted-glass bar (replaces the sidebar) */
[data-testid="stHeader"] { background: rgba(255,255,255,.68) !important; backdrop-filter: blur(18px) saturate(1.4);
  -webkit-backdrop-filter: blur(18px) saturate(1.4); border-bottom: 1px solid rgba(255,255,255,.9);
  box-shadow: 0 10px 30px -22px rgba(30,60,150,.55); }
[data-testid="stTopNavLink"], [data-testid="stTopNavSection"] { border-radius: 999px !important; padding: 4px 12px !important; transition: background .2s; }
[data-testid="stTopNavLink"]:hover, [data-testid="stTopNavSection"]:hover { background: rgba(34,211,197,.14) !important; }
[data-testid="stTopNavLink"][aria-current="page"] { background: linear-gradient(100deg, rgba(34,211,197,.22), rgba(79,107,255,.18)) !important; }
[data-testid="stTopNav"] p { font-weight: 600 !important; color: #1E2547 !important; }
[data-testid="stHeaderLogo"] { height: 30px !important; }
.ll-foot { text-align: center; color: #5A6386; font-size: 12.5px; padding: 26px 0 6px; }
.ll-foot a { color: #0E9F94; font-weight: 600; }

/* Sidebar: only used by Streamlit as the phone menu drawer (top menu on wider screens); light glass */
[data-testid="stSidebar"] { background: rgba(244,248,255,.94) !important; backdrop-filter: blur(18px);
                            border-right: 1px solid rgba(255,255,255,.9); }
[data-testid="stSidebarNav"] a { border-radius: 12px; }
[data-testid="stSidebarNav"] a[aria-current="page"] { background: linear-gradient(100deg, rgba(34,211,197,.22), rgba(79,107,255,.16)); }

/* Glass surfaces: custom cards, charts, tables, expanders */
.aur-card, [data-testid="stPlotlyChart"], [data-testid="stDataFrame"], [data-testid="stExpander"] details {
  background: rgba(255,255,255,.62) !important; border: 1px solid rgba(255,255,255,.85) !important; border-radius: 20px !important;
  backdrop-filter: blur(16px) saturate(1.3); -webkit-backdrop-filter: blur(16px) saturate(1.3);
  box-shadow: 0 22px 50px -30px rgba(40,70,160,.5), inset 0 1px 0 rgba(255,255,255,.8); }
[data-testid="stPlotlyChart"] { padding: 10px 12px 4px; }
[data-testid="stDataFrame"] { padding: 6px; }
.aur-card { padding: 18px 20px; transition: transform .3s, box-shadow .3s; animation: aurRise .6s cubic-bezier(.2,.7,.2,1) both; }
.aur-card:hover { transform: translateY(-4px); box-shadow: 0 30px 60px -30px rgba(40,90,200,.6), 0 0 0 1px rgba(34,211,197,.45); }
@keyframes aurRise { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: none; } }
.aur-label { color: #5A6386; font-size: 13px; }
.aur-big { font-family: 'Plus Jakarta Sans', sans-serif; font-size: 30px; font-weight: 800; letter-spacing: -.03em; margin: 4px 0 2px;
           background: linear-gradient(100deg, #0B5FB0, #2F6BFF 60%, #7C5CFF); -webkit-background-clip: text; background-clip: text; color: transparent; }
.aur-note { color: #0E9F94; font-size: 12.5px; font-weight: 600; }
.aur-pill { display: inline-block; padding: 3px 10px; border-radius: 99px; font-size: 12px; font-weight: 600; }
.aur-callout { border-left: 4px solid #22D3C5; background: rgba(255,255,255,.62); backdrop-filter: blur(10px); color: #1E2547;
               padding: 12px 16px; border-radius: 0 14px 14px 0; box-shadow: 0 14px 30px -24px rgba(40,70,160,.6); }
.aur-warn { border-left: 4px solid #FF7A6B; background: rgba(255,240,234,.88); color: #7A2E17; padding: 12px 16px; border-radius: 0 14px 14px 0; }

/* Buttons and inputs: teal → blue gradient, rounded shapes */
.stButton > button, .stDownloadButton > button { border-radius: 999px; border: 0; color: #fff !important; font-weight: 600;
    background: linear-gradient(110deg, #0E9F94, #14B8A6 45%, #22C4D8 75%, #4F6BFF); background-size: 180% auto;
    box-shadow: 0 12px 28px -14px rgba(16,170,160,.8); transition: background-position .5s, transform .25s; }
.stButton > button:hover, .stDownloadButton > button:hover { background-position: right center; transform: translateY(-2px); }
[data-baseweb="select"] > div, [data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea {
    border-radius: 14px !important; background: rgba(255,255,255,.78) !important; }
[data-testid="stTabs"] button[aria-selected="true"] p { color: #0E9F94 !important; font-weight: 600; }
[data-testid="stPageLink"] a { border-radius: 14px; background: rgba(255,255,255,.6); border: 1px solid rgba(255,255,255,.9); padding: 6px 12px; }
@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }
</style>
"""

# Glowing cursor + light trail (fine pointers only; injected once per browser tab)
CURSOR = """
<style>
@media (hover: hover) and (pointer: fine) {
  body.ll-cursor, body.ll-cursor * { cursor: none !important; }
  #ll-dot, #ll-ring { position: fixed; left: 0; top: 0; pointer-events: none; border-radius: 50%; translate: -50% -50%; z-index: 2147483647; }
  #ll-dot { width: 8px; height: 8px; background: #fff; box-shadow: 0 0 10px 3px rgba(34,211,197,.95), 0 0 24px 8px rgba(79,107,255,.45); }
  #ll-ring { width: 36px; height: 36px; border: 1.5px solid rgba(34,211,197,.85); box-shadow: 0 0 16px rgba(34,211,197,.4);
             transition: width .25s, height .25s, background .25s; }
  #ll-ring.hover { width: 60px; height: 60px; background: rgba(34,211,197,.12); }
  #ll-trail { position: fixed; inset: 0; pointer-events: none; z-index: 2147483646; }
}
</style>
<script>
(() => {
  if (window.__llCursor || !matchMedia("(hover: hover) and (pointer: fine)").matches || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  window.__llCursor = true;
  const d = document, dot = d.createElement("div"), ring = d.createElement("div"), cv = d.createElement("canvas");
  dot.id = "ll-dot"; ring.id = "ll-ring"; cv.id = "ll-trail"; d.body.append(cv, ring, dot); d.body.classList.add("ll-cursor");
  const ctx = cv.getContext("2d"), dpr = Math.min(devicePixelRatio || 1, 2);
  const size = () => { cv.width = innerWidth * dpr; cv.height = innerHeight * dpr; cv.style.width = innerWidth + "px";
                       cv.style.height = innerHeight + "px"; ctx.setTransform(dpr, 0, 0, dpr, 0, 0); };
  size(); addEventListener("resize", size);
  let mx = -99, my = -99, rx = mx, ry = my; const pts = [];
  addEventListener("pointermove", (e) => { mx = e.clientX; my = e.clientY; dot.style.transform = `translate3d(${mx}px,${my}px,0)`;
                                           pts.push({ x: mx, y: my, life: 1 }); if (pts.length > 50) pts.shift(); }, { passive: true });
  const hov = "a, button, [role=tab], [data-baseweb=select], summary, input, textarea";
  d.addEventListener("pointerover", (e) => { if (e.target.closest(hov)) ring.classList.add("hover"); });
  d.addEventListener("pointerout", (e) => { if (e.target.closest(hov)) ring.classList.remove("hover"); });
  (function loop() {
    rx += (mx - rx) * .2; ry += (my - ry) * .2; ring.style.transform = `translate3d(${rx}px,${ry}px,0)`;
    ctx.clearRect(0, 0, innerWidth, innerHeight);
    for (let i = 1; i < pts.length; i++) {
      const a = pts[i - 1], b = pts[i]; b.life -= .025; if (b.life <= 0) continue;
      ctx.strokeStyle = `rgba(34,211,197,${b.life * .5})`; ctx.lineWidth = 3 * b.life; ctx.lineCap = "round";
      ctx.shadowColor = "rgba(79,107,255,.7)"; ctx.shadowBlur = 10;
      ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
    }
    while (pts.length && pts[0].life <= 0) pts.shift();
    requestAnimationFrame(loop);
  })();
})();
</script>
"""


def setup(title: str) -> None:
    """Call first on every page: inject the theme CSS and the glowing cursor (wide layout is set in app.py)."""
    st.html(CSS)
    st.html(CURSOR, unsafe_allow_javascript=True)


@lru_cache(maxsize=None)
def _hero_image() -> str:
    f = STATIC / "hero.webp"
    return "data:image/webp;base64," + base64.b64encode(f.read_bytes()).decode() if f.exists() else ""


def hero(title: str, highlight: str, subtitle: str, eyebrow: str = "Live · public US data") -> None:
    """Light glass banner over the LaunchLens artwork (molecules, pen, globe), with a shimmering gradient word."""
    st.html(f"""
    <div class="ll-hero" style="background-image:url('{_hero_image()}')">
      <div class="veil"></div>
      <div class="inner">
        <span class="eyebrow"><span class="dot"></span>{eyebrow}</span>
        <h1>{title} <span class="grad">{highlight}</span></h1>
        <p>{subtitle}</p>
      </div>
    </div>
    <style>
      .ll-hero {{ position: relative; overflow: hidden; border-radius: 26px; padding: 34px 36px 38px; margin-bottom: 8px; min-height: 230px;
                  background-size: cover; background-position: 70% 40%; box-shadow: 0 30px 60px -36px rgba(40,70,160,.6);
                  border: 1px solid rgba(255,255,255,.9); }}
      .ll-hero .veil {{ position: absolute; inset: 0; background: linear-gradient(90deg, rgba(244,248,255,.97) 0%, rgba(244,248,255,.9) 38%,
                        rgba(244,248,255,.35) 68%, rgba(244,248,255,.05) 100%); }}
      .ll-hero .inner {{ position: relative; max-width: 720px; }}
      .ll-hero .eyebrow {{ display: inline-flex; gap: 8px; align-items: center; font-size: 12px; letter-spacing: .12em; text-transform: uppercase;
                           font-weight: 600; color: #0B1030; background: rgba(255,255,255,.75); border: 1px solid #fff; padding: 6px 13px;
                           border-radius: 99px; }}
      .ll-hero .dot {{ width: 8px; height: 8px; border-radius: 50%; background: #22D3C5; animation: llpulse 2s infinite; }}
      @keyframes llpulse {{ 0% {{ box-shadow: 0 0 0 0 rgba(34,211,197,.7); }} 70% {{ box-shadow: 0 0 0 10px rgba(34,211,197,0); }}
                            100% {{ box-shadow: 0 0 0 0 rgba(34,211,197,0); }} }}
      .ll-hero h1 {{ font-family: 'Plus Jakarta Sans', sans-serif; font-size: clamp(30px, 4.2vw, 50px); font-weight: 800; margin: 16px 0 8px;
                     color: #0B1030 !important; line-height: 1.05; letter-spacing: -.035em; }}
      .ll-hero .grad {{ background: linear-gradient(100deg, #0FA89A, #22D3C5 35%, #4F6BFF 70%, #0FA89A); background-size: 200% auto;
                        -webkit-background-clip: text; background-clip: text; color: transparent; animation: llshine 7s linear infinite; }}
      @keyframes llshine {{ to {{ background-position: 200% center; }} }}
      .ll-hero p {{ color: #3E4770; margin: 0; max-width: 620px; font-size: 15.5px; }}
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
