"""Doctor segmentation and a transparent targeting score for the 2026 GLP-1 opportunity
(Medicare GLP-1 Bridge from Jul 2026 + oral Foundayo launch).

Why a weighted score and not a black-box model? There is no label to learn from: nobody has observed
2026 doctor-level prescribing yet. So we encode commercial logic as **explicit, explainable components**,
each scaled 0–1, combine them with documented weights, test how sensitive the ranking is to those weights,
and attach plain-language **reasons** to every doctor. When 2026 data arrives, the components become
features for a supervised model and the weights can be learned instead of chosen.
"""
import numpy as np
import pandas as pd

from ..paths import PROCESSED

SCORES = PROCESSED / "targeting_scores.parquet"

# Component → weight (sums to 1). coverage_gap only exists once Open Payments is loaded;
# if it is missing, the remaining weights are re-normalised.
WEIGHTS = {
    "potential":           0.30,   # size of the diabetes patient base
    "glp1_experience":     0.20,   # already comfortable prescribing GLP-1s
    "headroom":            0.15,   # GLP-1s are a small share of their diabetes Rx → room to grow
    "tirzepatide_openness": 0.15,  # swing prescribers who already use both molecules
    "oral_affinity":       0.10,   # prescribes oral semaglutide (Rybelsus) → natural Foundayo audience
    "research":            0.05,   # publishes or runs GLP-1 trials (KOL signal)
    "coverage_gap":        0.05,   # no Lilly contact recorded in Open Payments
}
EXCLUDE_SPECIALTIES = {"Student in an Organized Health Care Education/Training Program"}

SEGMENTS = [   # evaluated in order; first match wins
    ("A · Tirzepatide champions",  "high GLP-1 volume, tirzepatide ≥ 50% vs semaglutide"),
    ("B · High-value swing",       "high GLP-1 volume, uses both molecules"),
    ("C · Competitor strongholds", "high GLP-1 volume, semaglutide ≥ 80%"),
    ("D · Untapped potential",     "large diabetes base, GLP-1 < 10% of diabetes Rx"),
    ("E · Developing GLP-1 users", "mid-volume GLP-1 prescribers"),
    ("F · Low volume",             "everyone else"),
]


def pct_rank(s: pd.Series) -> pd.Series:
    """Percentile rank 0–1 (ties share a rank); zeros stay at the bottom."""
    return s.rank(pct=True, method="average").fillna(0)


def components(hcp: pd.DataFrame) -> pd.DataFrame:
    """Every component on a 0–1 scale, one column each."""
    c = pd.DataFrame(index=hcp.index)
    c["potential"] = pct_rank(hcp["diabetes_total_claims"])
    c["glp1_experience"] = np.where(hcp["glp1_claims"] > 0, pct_rank(hcp["glp1_claims"].where(hcp["glp1_claims"] > 0)), 0)
    c["headroom"] = 1 - hcp["glp1_share_of_diabetes"].fillna(0)
    ts = hcp["tirzepatide_share"]
    c["tirzepatide_openness"] = np.select(
        [ts.isna() & ~hcp["glp1_adopter"], ts.isna(), ts.between(0.2, 0.8), ts > 0.8, ts < 0.2],
        [0.5,                               0.4,       1.0,                  0.6,      0.3])
    ryb = hcp["rybelsus_claims"]
    c["oral_affinity"] = np.where(ryb > 0, 0.5 + 0.5 * pct_rank(ryb.where(ryb > 0)), 0)
    research = hcp.get("pubmed_papers", 0) + 2 * hcp.get("trials", 0)
    c["research"] = np.minimum(1, research / 5)
    if "op_lilly_payments" in hcp:
        c["coverage_gap"] = (hcp["op_lilly_payments"].fillna(0) == 0).astype(float)
    return c


def weighted_score(comp: pd.DataFrame, weights: dict = WEIGHTS) -> pd.Series:
    w = {k: v for k, v in weights.items() if k in comp}
    total = sum(w.values())
    return 100 * sum(comp[k] * v for k, v in w.items()) / total


def segment(hcp: pd.DataFrame) -> pd.Series:
    d, g, ts = hcp["diabetes_decile"], hcp["glp1_decile"].astype("float"), hcp["tirzepatide_share"]
    share = hcp["glp1_share_of_diabetes"].fillna(0)
    conds = [
        (g <= 3) & (ts >= 0.5),
        (g <= 3) & (ts > 0.2),
        (g <= 3),
        (d <= 3) & (share < 0.10),
        g.between(4, 7),
    ]
    return pd.Series(np.select(conds, [s for s, _ in SEGMENTS[:5]], SEGMENTS[5][0]), index=hcp.index)


def reasons(hcp: pd.DataFrame, comp: pd.DataFrame, weights: dict = WEIGHTS, top: int = 3) -> pd.Series:
    """The `top` biggest weighted contributions per doctor, written as short evidence phrases."""
    w = {k: v for k, v in weights.items() if k in comp}
    contrib = pd.DataFrame({k: comp[k] * v for k, v in w.items()})

    def phrase(i, k):
        r = hcp.loc[i]
        return {
            "potential":            f"large diabetes patient base ({r.diabetes_total_claims:,.0f} diabetes claims, top {max(1, np.ceil(100 - 100 * comp.at[i, 'potential'])):.0f}%)",
            "glp1_experience":      f"experienced GLP-1 prescriber ({r.glp1_claims:,.0f} GLP-1 claims)",
            "headroom":             f"GLP-1s only {100 * (r.glp1_share_of_diabetes if pd.notna(r.glp1_share_of_diabetes) else 0):.0f}% of diabetes Rx: room to grow",
            "tirzepatide_openness": "already uses both tirzepatide and semaglutide" if comp.at[i, k] == 1 else "open to GLP-1 options",
            "oral_affinity":        f"prescribes oral semaglutide ({r.rybelsus_claims:,.0f} Rybelsus claims): relevant to oral Foundayo",
            "research":             "active in GLP-1 research (papers / trials)",
            "coverage_gap":         "no Lilly engagement recorded (possible coverage gap)",
        }[k]

    top_k = contrib.apply(lambda row: row.nlargest(top).index.tolist(), axis=1)
    return pd.Series([" · ".join(phrase(i, k) for k in ks if contrib.at[i, k] > 0) for i, ks in top_k.items()],
                     index=hcp.index)


def build(hcp: pd.DataFrame, kol: pd.DataFrame | None = None, with_reasons_top: int = 20000) -> pd.DataFrame:
    """Score, rank, segment and explain every eligible doctor; save to data/03_processed."""
    df = hcp.copy()
    if kol is not None:
        df = df.merge(kol, on="npi", how="left")
        for c in ["pubmed_papers", "pubmed_senior_author", "trials", "trials_tirzepatide_or_orfor"]:
            df[c] = df[c].fillna(0).astype(int)
    eligible = ~df["npi_deactivated"].fillna(False) & ~df["specialty"].isin(EXCLUDE_SPECIALTIES)
    df = df[eligible].reset_index(drop=True)

    comp = components(df)
    df["score"] = weighted_score(comp).round(1)
    df["rank"] = df["score"].rank(ascending=False, method="first").astype(int)
    df["segment"] = segment(df)
    for k in comp:
        df[f"c_{k}"] = comp[k].round(3)
    # Reasons are text-heavy; compute them for the top N (what the app actually shows)
    top = df.nsmallest(with_reasons_top, "rank").index
    df["reasons"] = ""
    df.loc[top, "reasons"] = reasons(df.loc[top], comp.loc[top])

    keep = ["npi", "last_name", "first_name", "city", "state", "practice_zip5", "specialty", "segment", "score", "rank",
            "reasons", "diabetes_total_claims", "glp1_claims", "glp1_share_of_diabetes", "tirzepatide_share",
            "rybelsus_claims", "pubmed_papers", "trials", *[c for c in df if c.startswith(("op_lilly", "op_novo", "c_"))]]
    out = df[[c for c in keep if c in df]].sort_values("rank")
    out.to_parquet(SCORES, index=False)
    return out


def weight_sensitivity(hcp_scored_components: pd.DataFrame, n: int = 50, jitter: float = 0.2,
                       top_k: int = 10000, seed: int = 0) -> pd.DataFrame:
    """Re-score with randomly perturbed weights (±jitter) and measure how stable the top-k list is."""
    rng = np.random.default_rng(seed)
    comp = hcp_scored_components
    base = weighted_score(comp)
    base_top = set(base.nlargest(top_k).index)
    rows = []
    for _ in range(n):
        w = {k: v * rng.uniform(1 - jitter, 1 + jitter) for k, v in WEIGHTS.items() if k in comp}
        s = weighted_score(comp, w)
        rows.append({"top_k_overlap": len(base_top & set(s.nlargest(top_k).index)) / top_k,
                     "spearman": base.rank().corr(s.rank())})
    return pd.DataFrame(rows)
