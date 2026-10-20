"""Pre-compute the small tables the Streamlit app reads (app/data/), so the app never touches raw files.

Run after notebooks 02–05:   python -m glp1_intel.app_data
Everything here is an aggregate or the scored-doctor list; the app loads it in well under a second.
"""
import json

import duckdb
import pandas as pd

from .models.targeting import weighted_score
from .paths import PART_D_2024_GLP1, PROCESSED, RAW, ROOT

APP_DATA = ROOT / "app" / "data"
MOLECULE = {"Tirzepatide": "tirzepatide", "Semaglutide": "semaglutide", "Dulaglutide": "dulaglutide",
            "Liraglutide": "liraglutide", "Insulin Degludec/Liraglutide": "liraglutide"}


def _brands() -> pd.DataFrame:
    df = duckdb.sql(f"""
        SELECT Brand AS brand, Generic AS generic, SUM(Tot_Clms) AS claims, SUM(Tot_Drug_Cst) AS cost,
               COUNT(DISTINCT Prscrbr_NPI) AS prescribers
        FROM read_parquet('{PART_D_2024_GLP1.as_posix()}') GROUP BY ALL ORDER BY claims DESC
    """).df()
    df["molecule"] = df["generic"].map(MOLECULE).fillna("other")
    return df


def _states(scores: pd.DataFrame) -> pd.DataFrame:
    st = duckdb.sql(f"""
        SELECT Prscrbr_State_Abrvtn AS state, SUM(Tot_Clms) AS glp1_claims, COUNT(DISTINCT Prscrbr_NPI) AS prescribers,
               SUM(Tot_Clms) FILTER (WHERE Generic = 'Tirzepatide') AS tirz,
               SUM(Tot_Clms) FILTER (WHERE Generic IN ('Tirzepatide', 'Semaglutide')) AS tirz_sema
        FROM read_parquet('{PART_D_2024_GLP1.as_posix()}') GROUP BY ALL
    """).df()
    st["tirz_share"] = 100 * st["tirz"] / st["tirz_sema"]
    top = scores[scores["rank"] <= 10_000]
    tgt = top.groupby("state").agg(top_targets=("npi", "size"),
                                   top_no_lilly=("op_lilly_payments", lambda s: (s == 0).sum())).reset_index()
    return st.drop(columns=["tirz", "tirz_sema"]).merge(tgt, on="state", how="left").fillna({"top_targets": 0, "top_no_lilly": 0})


def _specialties(hcp: pd.DataFrame) -> pd.DataFrame:
    g = hcp.groupby("specialty").agg(doctors=("npi", "size"), glp1_claims=("glp1_claims", "sum"),
                                     diabetes_claims=("diabetes_total_claims", "sum"),
                                     tirz=("tirzepatide_claims", "sum"), sema=("semaglutide_claims", "sum"),
                                     adopters=("glp1_adopter", "sum")).reset_index()
    g["tirz_share"] = 100 * g["tirz"] / (g["tirz"] + g["sema"]).where(lambda s: s > 0)
    g["pct_adopting"] = 100 * g["adopters"] / g["doctors"]
    return g.sort_values("glp1_claims", ascending=False).head(15).drop(columns=["tirz", "sema"])


def _medicaid() -> tuple[pd.DataFrame, pd.DataFrame]:
    s = pd.concat(pd.read_csv(f, dtype=str) for f in sorted((RAW / "medicaid_state_drug_utilization").glob("sdud_*_glp1.csv")))
    s = s[s["state"] != "XX"]
    s["rx"] = pd.to_numeric(s["number_of_prescriptions"])
    s["brand"] = s["product_name"].str.upper().str.extract(
        r"^(MOUNJARO|ZEPBOUND|OZEMPIC|WEGOVY|TRULICITY|RYBELSUS|SAXENDA)")[0].str.title()
    s["period"] = s["year"] + " Q" + s["quarter"]
    trend = s.dropna(subset=["brand"]).groupby(["period", "brand"])["rx"].sum().reset_index()
    ob = s[s["brand"].isin(["Zepbound", "Wegovy"])].pivot_table(index="state", columns="period", values="rx", aggfunc="sum").fillna(0)
    chg = pd.DataFrame({"state": ob.index, "q4_2025": ob["2025 Q4"].values, "q1_2026": ob["2026 Q1"].values})
    chg["pct"] = 100 * (chg["q1_2026"] / chg["q4_2025"].where(chg["q4_2025"] > 0) - 1)
    chg["ended_coverage"] = chg["state"].isin(["CA", "PA", "NH", "SC"])
    return trend, chg


def _faers() -> pd.DataFrame:
    return pd.read_csv(RAW / "fda_faers_side_effect_reports/faers_counts_glp1.csv", dtype={"term": str})


def build() -> dict:
    APP_DATA.mkdir(parents=True, exist_ok=True)
    hcp = pd.read_parquet(PROCESSED / "hcp_360.parquet")
    scores = pd.read_parquet(PROCESSED / "targeting_scores.parquet")

    brands = _brands()
    tables = {
        "brands": brands,
        "states": _states(scores),
        "specialties": _specialties(hcp),
        "faers": _faers(),
        "targets": scores,
        "segments": scores.groupby("segment").agg(doctors=("npi", "size"), diabetes_claims=("diabetes_total_claims", "sum"),
                                                  glp1_claims=("glp1_claims", "sum"), avg_score=("score", "mean")).reset_index(),
    }
    tables["medicaid_trend"], tables["medicaid_change"] = _medicaid()
    for name, df in tables.items():
        df.to_parquet(APP_DATA / f"{name}.parquet", index=False)

    tz = brands.loc[brands["generic"] == "Tirzepatide", "claims"].sum()
    sm = brands.loc[brands["generic"] == "Semaglutide", "claims"].sum()
    # Coverage gap measured on readiness WITHOUT the coverage bonus (avoids circular reasoning; see notebook 05)
    comp = scores[[c for c in scores if c.startswith("c_") and c != "c_coverage_gap"]].rename(columns=lambda c: c[2:])
    ready = scores.loc[weighted_score(comp).nlargest(10_000).index]
    kpis = {
        "prescribers": int(hcp["glp1_adopter"].sum()),
        "doctors_universe": int(len(hcp)),
        "glp1_claims": int(brands["claims"].sum()),
        "glp1_cost_bn": round(float(brands["cost"].sum()) / 1e9, 1),
        "tirz_share": round(float(100 * tz / (tz + sm)), 1),
        "ready_no_lilly_pct": round(100 * float((ready["op_lilly_payments"] == 0).mean()), 1),
        "ready_novo_not_lilly_pct": round(100 * float(((ready["op_lilly_payments"] == 0) & (ready["op_novo_payments"] > 0)).mean()), 1),
        "untapped_doctors": int((scores["segment"].str.startswith("D")).sum()),
        "medicaid_latest": "2026 Q1",
    }
    (APP_DATA / "kpis.json").write_text(json.dumps(kpis, indent=2))
    return kpis


if __name__ == "__main__":
    print(build())
