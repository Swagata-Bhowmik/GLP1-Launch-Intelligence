"""Build the one-file project report for reviewers from app/guide_content.py (the same text as the app's guide pages).

    python deploy/build_report.py

Writes docs/project_report.html (to attach or open offline) and app/static/site/report.html (linked from the website).
Figures from reports/figures are embedded, so the file works with no internet connection.
"""
import base64
import html
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
import guide_content as G  # noqa: E402

FIG = ROOT / "reports" / "figures"
OUT = [ROOT / "docs" / "project_report.html", ROOT / "app" / "static" / "site" / "report.html"]
STATUS = {"Met": "ok", "Met (dose weak)": "ok", "Partly": "mid", "Not met": "bad", "Gap found": "bad", "Not done": "na"}


def esc(s: str) -> str:
    """Escape text, then turn the content's **bold** markers into <b>."""
    parts = html.escape(s).split("**")
    return "".join(f"<b>{p}</b>" if i % 2 else p for i, p in enumerate(parts))


def img(name: str, caption: str) -> str:
    f = FIG / name
    if not f.exists():
        return ""
    data = base64.b64encode(f.read_bytes()).decode()
    return f'<figure><img src="data:image/png;base64,{data}" alt="{esc(caption)}" loading="lazy"><figcaption>{esc(caption)}</figcaption></figure>'


def table(head: list[str], rows: list[list[str]]) -> str:
    th = "".join(f"<th>{h}</th>" for h in head)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="tw"><table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>'


def a(url: str, text: str) -> str:
    return f'<a href="{url}" target="_blank" rel="noopener">{text}</a>'


S = G.SUMMARY
sections = []

sections.append(("review", "How to review this project", f"""
<p>Three places hold everything. Each step takes about five minutes.</p>
<ol class="steps">
  <li><b>Read this report</b> (you are here): the problem, the data, every notebook, the results and the decisions.</li>
  <li><b>Open the website:</b> {a(G.APP, "glp1-launchlens.streamlit.app")}. On the home page click <b>“Start here: project guide”</b>,
      or the green <b>“Open the app”</b> button for a numbered list of all pages. Every page starts with a
      <b>“This page answers”</b> box and a <b>“How to read this page”</b> panel.</li>
  <li><b>Check the code and notebooks:</b> {a(G.REPO, "GitHub repository")}. The README has the architecture, setup and results;
      the <code>notebooks/</code> folder holds the 16 notebooks with their outputs (links per notebook below).</li>
</ol>
<p class="note">The first visit to the website can take about a minute if the free server was asleep: click “Yes, get this app back up” and wait.
Live AI-writing features are switched off online because they need about 6 GB of memory; their evaluated outputs are shown instead.</p>"""))

sections.append(("summary", "The project in brief", f"""
<p class="lead">{esc(S["one_line"])}</p>
<div class="grid2">
  <div class="card"><h4>The problem</h4><p>{esc(S["problem"])}</p></div>
  <div class="card"><h4>What was built</h4><p>{esc(S["solution"])}</p></div>
  <div class="card"><h4>What is new, and what is not</h4><p>{esc(S["novelty"])}</p></div>
  <div class="card"><h4>Who it is for</h4><p>{esc(S["users"])}</p></div>
</div>
<div class="kpis">
  <div><b>199,831</b><span>GLP-1 prescribers (Medicare 2024)</span></div>
  <div><b>19.6M</b><span>GLP-1 claims · US$24.6bn</span></div>
  <div><b>308,303</b><span>doctors scored and ranked</span></div>
  <div><b>8,013</b><span>text chunks the AI can search</span></div>
</div>"""))

flow = ["Public data<small>Medicare · FDA · PubMed · 9 sources</small>", "HCP 360<small>316,559 doctors × 61 columns</small>",
        "Targeting<small>score + 6 segments</small>", "NLP models<small>classifiers · NER · side effects</small>",
        "Search + RAG<small>8,013 chunks, cited answers</small>", "Agent<small>5 tools, code computes numbers</small>",
        "Website<small>analyst + sales-rep views</small>"]
sections.append(("pipeline", "How it works", f"""
<div class="flow">{"".join(f'<div class="fnode">{x}</div>' for x in flow)}</div>
<p>Raw data is never edited: every change happens in code (<code>data/01_raw → 02_interim → 03_processed</code>).
The 4.4 GB Medicare file is queried with DuckDB straight from disk. Everything joins on the NPI, each US prescriber's ID.
Models and app tables are published on {a(G.HF, "Hugging Face")}; the app runs free on Streamlit Community Cloud.</p>"""))

sections.append(("data", "Data", table(["Dataset", "Source", "Contents", "Size", "Used for"],
                                       [[esc(c) for c in r] for r in G.DATA])
                 + '<p class="note">Public and synthetic data only. Doctor names come from public CMS registries.</p>'))

web = []
for i, (title, path, text) in enumerate(G.TOUR, 1):
    h = G.PAGE_HELP.get(path)
    detail = ""
    if h:
        detail = (f'<p><b>Answers:</b> {esc(h["question"])}</p><ul>' + "".join(f"<li>{esc(x)}</li>" for x in h["read"])
                  + f'</ul><p><b>What it means:</b> {esc(h["meaning"])}</p><p class="src">Source: {esc(h["source"])}</p>')
    web.append(f'<details class="pg"{" open" if i <= 3 else ""}><summary><span class="pn">{i}</span>{esc(title)}'
               f'<a class="open" href="{G.APP}{path}" target="_blank" rel="noopener">open ↗</a></summary>'
               f'<p>{esc(text)}</p>{detail}</details>')
sections.append(("website", "The website, page by page",
                 "<p>Click a page name to see what it shows and how to read its charts; “open ↗” opens the live page.</p>" + "".join(web)))

nbs = []
for nb in G.NOTEBOOKS:
    links = (f'<p class="links">{a(G.NBVIEWER + nb["file"], "view with outputs (nbviewer)")} · '
             f'{a(G.GITHUB_NB + nb["file"], "GitHub")}</p>') if nb["file"] else ""
    fig = img(nb["figure"], f"Notebook {nb['n']}") if nb["figure"] else ""
    nbs.append(f"""<details class="nb"><summary><span class="pn">{nb['n']}</span>{esc(nb['title'])}<em>{esc(nb['stage'])}</em></summary>
      <div class="nbb"><div><p><b>Why:</b> {esc(nb['why'])}</p><p><b>What was done:</b> {esc(nb['did'])}</p>
      <p><b>Key result:</b> {esc(nb['result'])}</p><p><b>Decision:</b> {esc(nb['decision'])}</p>
      <p><b>Used on the website:</b> {esc(nb['page'])}</p>{links}</div>{fig}</div></details>""")
sections.append(("notebooks", "Notebooks: what each one did",
                 "<p>A learning ladder: data → NLP basics → transformers → retrieval → RAG → agents → evaluation. "
                 "Each notebook explains the theory in plain language, applies it, and saves what the next one needs.</p>"
                 '<p><button class="mini" onclick="document.querySelectorAll(\'details.nb\').forEach(d=>d.open=true)">Open all</button> '
                 '<button class="mini" onclick="document.querySelectorAll(\'details.nb\').forEach(d=>d.open=false)">Close all</button></p>'
                 + "".join(nbs)))

res_rows = [[esc(g), esc(r), f'<span class="st {STATUS[s]}">{esc(s)}</span>'] for g, r, s in G.RESULTS]
sections.append(("results", "Targets vs results",
                 "<p>Brackets are 95% intervals. Failures are listed with the successes.</p>"
                 + table(["Goal", "Result", "Status"], res_rows)
                 + img("17_1_scorecard_intervals.png", "Every result with its 95% interval (notebook 17)")))

sections.append(("decisions", "Design decisions and why",
                 table(["#", "Decision", "Instead of", "Why", "Notebook"],
                       [[str(i), f"<b>{esc(d)}</b>", esc(alt), esc(w), esc(nb)] for i, (d, alt, w, nb) in enumerate(G.DECISIONS, 1)])))

sections.append(("limits", "Limitations and future work",
                 "<ul>" + "".join(f"<li>{esc(x)}</li>" for x in G.LIMITATIONS) + "</ul>"
                 + img("17_2_targeting_representation.png", "Fairness check: who the score selects vs who prescribes (notebook 17)")
                 + "<p><b>Next steps:</b> LoRA fine-tuning (notebook 16) on a free GPU; a larger LLM for RAG and the agent; a human check of "
                   "100 synthetic notes; screening documents against prompt injection; testing on real, consented field notes.</p>"))

sections.append(("where", "Where to find what", table(["If you want to know…", "Go to", "Notebook"],
                                                      [[esc(q), esc(p), esc(n)] for q, p, n in G.WHERE])))
sections.append(("glossary", "Glossary", "<dl>" + "".join(f"<dt>{esc(t)}</dt><dd>{esc(m)}</dd>" for t, m in G.GLOSSARY) + "</dl>"))

toc = "".join(f'<a href="#{sid}">{esc(title)}</a>' for sid, title, _ in sections)
body = "".join(f'<section id="{sid}"><h2>{esc(title)}</h2>{content}</section>' for sid, title, content in sections)

PAGE = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>LaunchLens project report</title>
<meta name="description" content="GLP-1 Launch Intelligence (LaunchLens): one-page project report for reviewers.">
<style>
:root {{ --ink:#0B1030; --text:#1E2547; --muted:#5A6386; --line:#E4E8F5; --bg:#F4F8FF; --card:#FFFFFF; --teal:#0E9F94; --blue:#4F6BFF;
        --ok:#E3F8F5; --okf:#0E7C72; --mid:#FFF6E0; --midf:#8A5A00; --bad:#FFECE6; --badf:#A63A1A; --na:#EEEDF3; --naf:#4A4570; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --ink:#F2F4FF; --text:#D9DEF2; --muted:#9AA3C7; --line:#2A3152;
        --bg:#0D1124; --card:#151A33; --ok:#0F3B37; --okf:#7EE3D6; --mid:#3D3110; --midf:#F5C96B; --bad:#3E1E17; --badf:#FFB4A0; --na:#252A44; --naf:#C3C6DD; }} }}
* {{ box-sizing:border-box }}
body {{ margin:0; background:var(--bg); color:var(--text); font:16px/1.6 "Segoe UI", Inter, system-ui, sans-serif; }}
a {{ color:var(--blue) }}
header {{ background:linear-gradient(120deg,#0E9F94,#22C4D8 45%,#4F6BFF); color:#fff; padding:44px 6vw 36px; }}
header h1 {{ margin:0 0 6px; font-size:clamp(28px,4vw,42px); letter-spacing:-.02em }}
header p {{ margin:4px 0; opacity:.95; max-width:860px }}
header .links a {{ color:#fff; font-weight:600; margin-right:18px }}
.wrap {{ display:grid; grid-template-columns:230px minmax(0,1fr); gap:34px; padding:30px 6vw 60px; max-width:1400px; margin:auto }}
nav.toc {{ position:sticky; top:20px; align-self:start; display:flex; flex-direction:column; gap:4px; font-size:14.5px }}
nav.toc a {{ color:var(--text); text-decoration:none; padding:6px 10px; border-radius:10px }}
nav.toc a:hover {{ background:var(--card) }}
section {{ background:var(--card); border:1px solid var(--line); border-radius:18px; padding:24px 28px; margin-bottom:22px }}
h2 {{ margin:0 0 12px; color:var(--ink); font-size:24px }} h4 {{ margin:0 0 6px; color:var(--ink) }}
.lead {{ font-size:18px; color:var(--ink) }}
.grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:14px }}
.card {{ border:1px solid var(--line); border-radius:14px; padding:14px 16px }} .card p {{ margin:0 }}
.kpis {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-top:16px }}
.kpis div {{ border:1px solid var(--line); border-radius:14px; padding:12px 14px }}
.kpis b {{ display:block; font-size:26px; color:var(--blue) }} .kpis span {{ color:var(--muted); font-size:13.5px }}
.flow {{ display:flex; flex-wrap:wrap; gap:8px; margin:6px 0 14px }}
.fnode {{ flex:1 1 120px; border:1px solid var(--line); border-radius:12px; padding:10px; font-weight:600; color:var(--ink); position:relative }}
.fnode small {{ display:block; font-weight:400; color:var(--muted); font-size:12.5px }}
.tw {{ overflow-x:auto }} table {{ width:100%; border-collapse:collapse; font-size:14.5px }}
th {{ text-align:left; color:var(--muted); font-weight:600; border-bottom:2px solid var(--line); padding:8px }}
td {{ border-bottom:1px solid var(--line); padding:8px; vertical-align:top }}
.st {{ padding:2px 10px; border-radius:99px; font-size:12.5px; font-weight:600; white-space:nowrap }}
.ok {{ background:var(--ok); color:var(--okf) }} .mid {{ background:var(--mid); color:var(--midf) }}
.bad {{ background:var(--bad); color:var(--badf) }} .na {{ background:var(--na); color:var(--naf) }}
details {{ border:1px solid var(--line); border-radius:14px; margin:10px 0; padding:0 16px }}
summary {{ cursor:pointer; padding:12px 0; font-weight:600; color:var(--ink); display:flex; align-items:center; gap:10px; list-style:none }}
summary::-webkit-details-marker {{ display:none }}
summary em {{ margin-left:auto; font-style:normal; font-weight:500; color:var(--muted); font-size:13px }}
.pn {{ flex:none; width:30px; height:30px; border-radius:50%; display:grid; place-items:center; color:#fff; font-size:13px;
       background:linear-gradient(120deg,#0E9F94,#4F6BFF) }}
summary .open {{ margin-left:auto; font-weight:500; font-size:14px }}
.nbb {{ display:grid; grid-template-columns:minmax(0,1.1fr) minmax(0,1fr); gap:18px; padding-bottom:14px }}
.nbb p {{ margin:6px 0 }}
figure {{ margin:10px 0 }} figure img {{ width:100%; border-radius:10px; border:1px solid var(--line); background:#fff }}
figcaption {{ color:var(--muted); font-size:13px }}
.note, .src {{ color:var(--muted); font-size:14px }}
.steps li {{ margin-bottom:8px }}
dl {{ display:grid; grid-template-columns:220px 1fr; gap:6px 16px; margin:0 }} dt {{ font-weight:600; color:var(--ink) }} dd {{ margin:0 }}
.mini {{ border:1px solid var(--line); background:var(--card); color:var(--text); border-radius:99px; padding:4px 12px; cursor:pointer }}
code {{ background:var(--bg); padding:1px 5px; border-radius:5px }}
footer {{ text-align:center; color:var(--muted); font-size:13px; padding:0 6vw 40px }}
@media (max-width:900px) {{ .wrap {{ grid-template-columns:1fr; padding:20px 16px 40px }} nav.toc {{ position:static; flex-direction:row; flex-wrap:wrap }}
  .grid2, .nbb {{ grid-template-columns:1fr }} .kpis {{ grid-template-columns:1fr 1fr }} dl {{ grid-template-columns:1fr }}
  header {{ padding:30px 16px }} section {{ padding:18px 16px }} }}
@media print {{ nav.toc, .mini {{ display:none }} .wrap {{ display:block; padding:0 }} details {{ break-inside:avoid }}
  section {{ break-inside:auto; border:0 }} header {{ -webkit-print-color-adjust:exact; print-color-adjust:exact }} }}
</style></head>
<body>
<header>
  <h1>LaunchLens · GLP-1 Launch Intelligence</h1>
  <p>{esc(S["one_line"])}</p>
  <p><b>Swagata Bhowmik</b> · MSc Data Science, NMIMS · project report, {date.today():%B %Y}</p>
  <p class="links">{a(G.APP, "Live website ↗")} {a(G.REPO, "GitHub ↗")} {a(G.HF, "Hugging Face ↗")}</p>
</header>
<div class="wrap"><nav class="toc" aria-label="Contents">{toc}</nav><main>{body}</main></div>
<footer>Independent portfolio project on public and synthetic data. Not affiliated with any pharmaceutical company. Not medical advice.</footer>
<script>window.matchMedia("print").addListener(m => m.matches && document.querySelectorAll("details").forEach(d => d.open = true));
window.addEventListener("beforeprint", () => document.querySelectorAll("details").forEach(d => d.open = true));</script>
</body></html>"""

for out in OUT:
    out.write_text(PAGE, encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)} ({out.stat().st_size / 1e6:.1f} MB)")
