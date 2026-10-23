"""Tools for the Ask-AI agent (notebook 15). Each tool is a plain, deterministic Python function: the LLM only
chooses which one to call and with which arguments; the numbers always come from code.

The docstrings and type hints are the tool descriptions the LLM sees (transformers turns them into JSON schemas).
"""
from functools import lru_cache

import pandas as pd

from glp1_intel.paths import PROCESSED, RAW

US_STATES = {"alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA", "colorado": "CO",
             "connecticut": "CT", "delaware": "DE", "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
             "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS", "kentucky": "KY", "louisiana": "LA",
             "maine": "ME", "maryland": "MD", "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
             "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
             "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY", "north carolina": "NC",
             "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA",
             "rhode island": "RI", "south carolina": "SC", "south dakota": "SD", "tennessee": "TN", "texas": "TX",
             "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
             "wisconsin": "WI", "wyoming": "WY", "district of columbia": "DC"}
BRAND_MOLECULE = {"mounjaro": "tirzepatide", "zepbound": "tirzepatide", "ozempic": "semaglutide", "wegovy": "semaglutide",
                  "rybelsus": "semaglutide", "trulicity": "dulaglutide", "victoza": "liraglutide", "saxenda": "liraglutide",
                  "foundayo": "orforglipron"}


def _state(s):
    if not s:
        return None
    s = str(s).strip()
    return US_STATES.get(s.lower(), s.upper()[:2])


@lru_cache(maxsize=None)
def _scores() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED / "targeting_scores.parquet")


@lru_cache(maxsize=None)
def _faers() -> pd.DataFrame:
    return pd.read_csv(RAW / "fda_faers_side_effect_reports" / "faers_counts_glp1.csv")


def top_doctors(state: str = "", specialty: str = "", segment: str = "", n: int = 5) -> str:
    """
    Rank US doctors by the GLP-1 targeting score (Medicare Part D 2024 prescribing, research, segment).

    Args:
        state: US state as a 2-letter code or name, e.g. "OH" or "Ohio". Empty for all states.
        specialty: Doctor specialty, e.g. "Endocrinology", "Family Practice", "Cardiology". Empty for all.
        segment: Segment letter A-F (A tirzepatide champions, B high-value swing, C competitor strongholds,
            D untapped potential, E developing users, F low volume). Empty for all.
        n: How many doctors to return (1-10).
    """
    df = _scores()
    if state:
        df = df[df["state"] == _state(state)]
    if specialty:
        df = df[df["specialty"].str.contains(specialty, case=False, regex=False)]
    if segment:
        df = df[df["segment"].str.startswith(segment.strip().upper()[:1])]
    top = df.nsmallest(max(1, min(int(n), 10)), "rank")
    if top.empty:
        return "No doctors match these filters."
    lines = [f"{len(df):,} doctors match. Top {len(top)} by targeting score (names hidden):"]
    for r in top.itertuples():
        lines.append(f"- NPI {str(r.npi)[:3]}••••••• · {r.specialty} · {r.state} · rank {int(r.rank):,} · score {r.score:.1f} · "
                     f"segment {r.segment} · {int(r.glp1_claims):,} GLP-1 claims · tirzepatide share {r.tirzepatide_share:.0%} · "
                     f"why: {r.reasons}")
    return "\n".join(lines)


def market_summary(state: str = "") -> str:
    """
    GLP-1 prescribing summary from Medicare Part D 2024: doctors, claims, tirzepatide share and oral share.

    Args:
        state: US state as a 2-letter code or name. Empty for the whole US.
    """
    df = _scores()
    where = "US"
    if state:
        where = _state(state)
        df = df[df["state"] == where]
        if df.empty:
            return f"No data for state '{state}'."
    glp1 = df["glp1_claims"].sum()
    tirz = (df["glp1_claims"] * df["tirzepatide_share"]).sum()
    seg = df["segment"].str[0].value_counts().reindex(list("ABCDEF"), fill_value=0)
    return (f"{where}, Medicare Part D 2024: {len(df):,} eligible prescribers, {glp1:,.0f} GLP-1 claims, "
            f"tirzepatide share {tirz / glp1:.0%}, oral semaglutide (Rybelsus) {df['rybelsus_claims'].sum() / glp1:.1%} of GLP-1 claims. "
            f"Doctors per segment: " + ", ".join(f"{k} {v:,}" for k, v in seg.items()) + ".")


def side_effect_reports(drug: str, top: int = 5) -> str:
    """
    Most frequently reported side effects in FDA FAERS (2022 - mid 2026) for a GLP-1 drug. Reports are
    voluntary and do not prove the drug caused the event or show how common it is.

    Args:
        drug: Brand or molecule, e.g. "Mounjaro", "tirzepatide", "Ozempic", "semaglutide", "Foundayo".
        top: How many reactions to list (1-10).
    """
    mol = BRAND_MOLECULE.get(drug.strip().lower(), drug.strip().lower())
    f = _faers()
    r = f[(f["drug"] == mol) & (f["count_type"] == "reactions")].nlargest(max(1, min(int(top), 10)), "count")
    if r.empty:
        return f"No FAERS data for '{drug}'. Available molecules: {', '.join(f['drug'].unique())}."
    total = f[(f["drug"] == mol) & (f["count_type"] == "reports_per_quarter")]["count"].sum()
    return (f"FAERS {mol} ({total:,} reports 2022Q1-2026Q2). Top reported reactions: "
            + "; ".join(f"{t.title()} {c:,}" for t, c in zip(r["term"], r["count"])) + ".")


@lru_cache(maxsize=None)
def _retriever():
    from glp1_intel.rag import knowledge_base as K, retrieval as R
    return R.Retriever(K.build())


def label_answer(question: str, brand: str) -> str:
    """
    Answer a question from the official FDA prescribing label of one drug (indication, dosing, warnings,
    side effects, interactions, storage), with citations. Uses retrieval + the guard from notebook 14.

    Args:
        question: The question about the drug label.
        brand: Brand name: Foundayo, Mounjaro, Zepbound, Ozempic, Wegovy, Rybelsus, Trulicity, Victoza or Saxenda.
    """
    from glp1_intel.rag import generate as G
    b = brand.strip().lower()
    if b not in BRAND_MOLECULE:
        return f"Unknown brand '{brand}'. Use one of: {', '.join(x.title() for x in BRAND_MOLECULE)}."
    res = G.answer(question, _retriever(), brand=b, source="label", method="hybrid", rerank=True)
    g = G.guard(res["answer"], res["sources"])
    if g["action"] == "block":
        return f"{G.NOT_FOUND} (answer blocked: {g['reason']})"
    cites = "; ".join(f"[{i}] {G.source_header(r)}" for i, (_, r) in enumerate(res["sources"].iterrows(), 1))
    flag = " (flagged for human review: not fully supported)" if g["action"] == "flag for review" else ""
    return f"{res['answer']}{flag}\nSources: {cites}"


def visit_note_insights(topic: str) -> str:
    """
    Search field-rep visit notes (synthetic dataset) for a topic and summarise which doctor objections appear.

    Args:
        topic: What to look for, e.g. "cost and insurance concerns", "needle fear", "GI side effects".
    """
    ret = _retriever()
    hits = ret.search(topic, k=20, source="note", method="hybrid")
    obj = hits["objections"].explode().dropna().value_counts()
    ex = " | ".join(hits["text"].head(2).str[:160])
    return (f"Top 20 of 1,055 visit notes for '{topic}'. Objections in them: "
            + ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in obj.head(5).items()) + f". Examples: {ex}")


TOOLS = [top_doctors, market_summary, side_effect_reports, label_answer, visit_note_insights]
TOOL_MAP = {t.__name__: t for t in TOOLS}
