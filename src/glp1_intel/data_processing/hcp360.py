"""HCP 360: one row per prescriber, joining every public source on NPI.

Universe = every Medicare Part D prescriber in 2024 who wrote a GLP-1 **or** any other diabetes drug.
Including diabetes prescribers with **zero** GLP-1 claims ("non-adopters") is deliberate: for targeting,
the doctor who treats many diabetes patients but has not started GLP-1s is often the biggest opportunity.

Pipeline (each step writes a file, so later steps are fast and re-runnable):
    1. prescriber_profile()  4.4 GB Part D CSV  → data/02_interim/part_d_2024_prescriber_profile.parquet
    2. nppes.build(npis)     NPPES bulk zip     → data/02_interim/nppes_hcp_universe.parquet
    3. payments_features()   Open Payments      → per-NPI Lilly / Novo engagement (if downloaded)
    4. build()               join everything    → data/03_processed/hcp_360.parquet
"""
import duckdb
import pandas as pd

from ..paths import INTERIM, PART_D_2024_GLP1, PROCESSED, RAW

PART_D_CSV = RAW / "medicare_part_d_prescribers/medicare_part_d_prescribers_by_provider_and_drug_2024.csv"
PROFILE = INTERIM / "part_d_2024_prescriber_profile.parquet"
NPPES_UNIVERSE = INTERIM / "nppes_hcp_universe.parquet"
OP_DIR = RAW / "open_payments_industry_to_doctor"
SDUD_DIR = RAW / "medicaid_state_drug_utilization"
HCP_360 = PROCESSED / "hcp_360.parquet"

# Non-GLP-1 diabetes drug classes, matched on the lower-cased generic name (first match wins,
# so combinations like "Empagliflozin/Metformin" count once, in the newer class).
DIABETES_CLASSES = {
    "sglt2":     "gliflozin",
    "dpp4":      "gliptin",
    "insulin":   "insulin",
    "su":        "glipizide|glimepiride|glyburide",          # sulfonylureas
    "tzd":       "pioglitazone",                              # thiazolidinediones
    "metformin": "metformin",
    "other_oral": "acarbose|repaglinide|nateglinide|pramlintide",
}
DEVICES = "syringe|needle|pump|device"                        # supplies, not drugs
GLP1_BRANDS_OP = ["mounjaro", "zepbound", "trulicity", "foundayo", "ozempic", "wegovy", "rybelsus",
                  "victoza", "saxenda", "xultophy"]           # product names in Open Payments


def _class_case() -> str:
    """SQL CASE expression that assigns each row to a diabetes class (or NULL)."""
    whens = "\n".join(f"WHEN regexp_matches(g, '{pat}') THEN '{cls}'" for cls, pat in DIABETES_CLASSES.items())
    return f"CASE WHEN regexp_matches(g, '{DEVICES}') THEN NULL WHEN g = 'insulin degludec/liraglutide' THEN NULL\n{whens}\nELSE NULL END"


def prescriber_profile(overwrite: bool = False) -> pd.DataFrame:
    """One pass over the full Part D file: practice size + non-GLP-1 diabetes claims per prescriber."""
    if PROFILE.exists() and not overwrite:
        return pd.read_parquet(PROFILE)
    src = f"read_csv('{PART_D_CSV.as_posix()}', header=true, types={{'Prscrbr_NPI':'VARCHAR','Prscrbr_State_FIPS':'VARCHAR'}})"
    class_cols = ",\n".join(f"SUM(Tot_Clms) FILTER (WHERE cls = '{c}') AS dm_{c}_claims" for c in DIABETES_CLASSES)
    duckdb.sql(f"""
        COPY (
            WITH rows AS (
                SELECT *, lower(trim(Gnrc_Name)) AS g FROM {src}
            ), tagged AS (
                SELECT *, {_class_case()} AS cls FROM rows
            )
            SELECT  Prscrbr_NPI                            AS npi,
                    any_value(Prscrbr_Last_Org_Name)       AS last_name,
                    any_value(Prscrbr_First_Name)          AS first_name,
                    any_value(Prscrbr_City)                AS city,
                    any_value(Prscrbr_State_Abrvtn)        AS state,
                    any_value(Prscrbr_State_FIPS)          AS state_fips,
                    any_value(Prscrbr_Type)                AS specialty,
                    SUM(Tot_Clms)                          AS all_drug_claims,
                    SUM(Tot_Drug_Cst)                      AS all_drug_cost,
                    COUNT(*)                               AS n_drugs,
                    {class_cols},
                    SUM(Tot_Clms) FILTER (WHERE cls IS NOT NULL) AS dm_non_glp1_claims
            FROM tagged
            GROUP BY 1
        ) TO '{PROFILE.as_posix()}' (FORMAT parquet, COMPRESSION zstd)
    """)
    return pd.read_parquet(PROFILE)


def glp1_features() -> str:
    """SQL for per-NPI GLP-1 metrics from the notebook-02 subset."""
    brands = {"mounjaro": "Mounjaro", "zepbound": "Zepbound", "ozempic": "Ozempic", "wegovy": "Wegovy",
              "rybelsus": "Rybelsus", "trulicity": "Trulicity"}
    brand_cols = ",\n".join(f"COALESCE(SUM(Tot_Clms) FILTER (WHERE Brand = '{b}'), 0) AS {k}_claims" for k, b in brands.items())
    return f"""
        SELECT  Prscrbr_NPI                                                         AS npi,
                SUM(Tot_Clms)                                                       AS glp1_claims,
                SUM(Tot_Drug_Cst)                                                   AS glp1_cost,
                SUM(Tot_Benes)                                                      AS glp1_benes_known,
                COUNT(*) FILTER (WHERE Tot_Benes IS NULL)                           AS glp1_rows_benes_suppressed,
                COUNT(DISTINCT Brand)                                               AS glp1_n_brands,
                COALESCE(SUM(Tot_Clms) FILTER (WHERE Generic = 'Tirzepatide'), 0)   AS tirzepatide_claims,
                COALESCE(SUM(Tot_Clms) FILTER (WHERE Generic = 'Semaglutide'), 0)   AS semaglutide_claims,
                COALESCE(SUM(Tot_Clms) FILTER (WHERE Generic = 'Dulaglutide'), 0)   AS dulaglutide_claims,
                COALESCE(SUM(Tot_Clms) FILTER (WHERE Generic ILIKE '%liraglutide%'), 0) AS liraglutide_claims,
                COALESCE(SUM(Tot_Clms) FILTER (WHERE Generic ILIKE 'exenatide%'), 0)    AS exenatide_claims,
                {brand_cols},
                SUM(GE65_Tot_Clms)                                                  AS glp1_ge65_claims_known
        FROM    read_parquet('{PART_D_2024_GLP1.as_posix()}')
        GROUP BY 1
    """


def payments_features() -> str | None:
    """SQL for per-NPI Open Payments features, or None if no finished download exists yet."""
    files = sorted(OP_DIR.glob("open_payments_general_*_lilly_novo.parquet"))
    if not files:
        return None
    src = " UNION ALL ".join(f"SELECT * FROM read_parquet('{f.as_posix()}')" for f in files)
    glp1_list = ", ".join(f"'{b}'" for b in GLP1_BRANDS_OP)
    cols = []
    for co, pat in [("lilly", "%lilly%"), ("novo", "%novo nordisk%")]:
        is_co = f"Applicable_Manufacturer_or_Applicable_GPO_Making_Payment_Name ILIKE '{pat}'"
        cols += [
            f"COUNT(*) FILTER (WHERE {is_co})                                              AS op_{co}_payments",
            f"COALESCE(SUM(amt) FILTER (WHERE {is_co}), 0)                                 AS op_{co}_usd",
            f"COUNT(*) FILTER (WHERE {is_co} AND drug IN ({glp1_list}))                    AS op_{co}_glp1_payments",
            f"COUNT(*) FILTER (WHERE {is_co} AND nature ILIKE 'Food and Beverage')         AS op_{co}_meals",
            f"COALESCE(SUM(amt) FILTER (WHERE {is_co} AND (nature ILIKE '%speaker%' OR nature ILIKE '%faculty%' "
            f"OR nature ILIKE 'Consulting Fee')), 0)                                       AS op_{co}_speaker_consult_usd",
        ]
    years = ", ".join(sorted(f.name.split("_")[3] for f in files))
    return f"""
        WITH p AS (
            SELECT  Covered_Recipient_NPI                                          AS npi,
                    Applicable_Manufacturer_or_Applicable_GPO_Making_Payment_Name,
                    TRY_CAST(Total_Amount_of_Payment_USDollars AS DOUBLE)          AS amt,
                    lower(trim(Name_of_Drug_or_Biological_or_Device_or_Medical_Supply_1)) AS drug,
                    Nature_of_Payment_or_Transfer_of_Value                         AS nature
            FROM    ({src})
            WHERE   Covered_Recipient_NPI IS NOT NULL
        )
        SELECT npi, {', '.join(cols)}, '{years}' AS op_years
        FROM p GROUP BY npi
    """


def state_context() -> pd.DataFrame:
    """State-level 2025 Medicaid obesity-GLP-1 volume and growth (Zepbound + Wegovy + Saxenda)."""
    frames = [pd.read_csv(f, dtype=str) for f in sorted(SDUD_DIR.glob("sdud_*_glp1.csv"))]
    s = pd.concat(frames)
    s = s[s["state"] != "XX"]
    s["rx"] = pd.to_numeric(s["number_of_prescriptions"])
    s = s[s["product_name"].str.upper().str.match("ZEPBOUND|WEGOVY|SAXENDA")]
    piv = s.pivot_table(index="state", columns="year", values="rx", aggfunc="sum").fillna(0)
    out = pd.DataFrame({
        "state": piv.index,
        "state_medicaid_obesity_rx_2025": piv.get("2025", 0).values,
        "state_medicaid_obesity_growth_24_25": ((piv.get("2025", 0) + 1) / (piv.get("2024", 0) + 1)).round(2).values,
    })
    return out


def build(overwrite: bool = False) -> pd.DataFrame:
    """Join all sources into the HCP 360 table (one row per NPI)."""
    from ..data_collection import nppes

    profile = prescriber_profile()
    universe = profile[(profile["dm_non_glp1_claims"].fillna(0) > 0) | profile["npi"].isin(
        duckdb.sql(f"SELECT DISTINCT Prscrbr_NPI FROM read_parquet('{PART_D_2024_GLP1.as_posix()}')").df()["Prscrbr_NPI"])]
    npi_reg = nppes.build(npis=set(universe["npi"]), out=NPPES_UNIVERSE)
    states = state_context()

    con = duckdb.connect()
    con.register("universe", universe)
    con.register("npi_reg", npi_reg)
    con.register("states", states)
    pay_sql = payments_features()
    pay_join = f"LEFT JOIN ({pay_sql}) pay USING (npi)" if pay_sql else ""
    pay_cols = "pay.* EXCLUDE (npi)," if pay_sql else ""

    df = con.sql(f"""
        WITH g AS ({glp1_features()})
        SELECT
            u.npi, u.last_name, u.first_name, u.city, u.state, u.state_fips, u.specialty,
            r.credential, r.sex, r.practice_zip5, r.taxonomy_1 AS taxonomy,
            TRY_CAST(right(r.enumeration_date, 4) AS INT)              AS npi_year,
            r.deactivation_date IS NOT NULL AND r.deactivation_date <> '' AS npi_deactivated,
            u.all_drug_claims, u.all_drug_cost, u.n_drugs,
            COALESCE(u.dm_non_glp1_claims, 0)                          AS dm_non_glp1_claims,
            {", ".join(f"COALESCE(u.dm_{c}_claims, 0) AS dm_{c}_claims" for c in DIABETES_CLASSES)},
            COALESCE(g.glp1_claims, 0)                                 AS glp1_claims,
            COALESCE(g.glp1_cost, 0)                                   AS glp1_cost,
            g.glp1_benes_known, g.glp1_rows_benes_suppressed, COALESCE(g.glp1_n_brands, 0) AS glp1_n_brands,
            COALESCE(g.tirzepatide_claims, 0) AS tirzepatide_claims, COALESCE(g.semaglutide_claims, 0) AS semaglutide_claims,
            COALESCE(g.dulaglutide_claims, 0) AS dulaglutide_claims, COALESCE(g.liraglutide_claims, 0) AS liraglutide_claims,
            COALESCE(g.exenatide_claims, 0)   AS exenatide_claims,
            COALESCE(g.mounjaro_claims, 0) AS mounjaro_claims, COALESCE(g.zepbound_claims, 0) AS zepbound_claims,
            COALESCE(g.ozempic_claims, 0)  AS ozempic_claims,  COALESCE(g.wegovy_claims, 0)   AS wegovy_claims,
            COALESCE(g.rybelsus_claims, 0) AS rybelsus_claims, COALESCE(g.trulicity_claims, 0) AS trulicity_claims,
            g.glp1_ge65_claims_known,
            {pay_cols}
            s.state_medicaid_obesity_rx_2025, s.state_medicaid_obesity_growth_24_25
        FROM universe u
        LEFT JOIN npi_reg r USING (npi)
        LEFT JOIN g USING (npi)
        {pay_join}
        LEFT JOIN states s USING (state)
    """).df()

    # No Open Payments record = no reported payment, a true zero (unlike a missing registry record)
    op_num = [c for c in df.columns if c.startswith("op_") and c != "op_years"]
    df[op_num] = df[op_num].fillna(0)
    if "op_years" in df:
        df["op_years"] = df["op_years"].fillna(df["op_years"].dropna().iloc[0] if df["op_years"].notna().any() else "")

    # ── Derived features (the "why" columns a targeting model and an analyst both use) ──
    dm_total = df["glp1_claims"] + df["dm_non_glp1_claims"]
    df["diabetes_total_claims"] = dm_total                                       # GLP-1 + other diabetes drugs
    df["glp1_adopter"] = df["glp1_claims"] > 0
    df["glp1_share_of_diabetes"] = (df["glp1_claims"] / dm_total.where(dm_total > 0)).round(3)
    tz_sm = df["tirzepatide_claims"] + df["semaglutide_claims"]
    df["tirzepatide_share"] = (df["tirzepatide_claims"] / tz_sm.where(tz_sm > 0)).round(3)
    df["lilly_glp1_share"] = ((df["tirzepatide_claims"] + df["dulaglutide_claims"])
                              / df["glp1_claims"].where(df["glp1_claims"] > 0)).round(3)
    df["glp1_decile"] = pd.NA                                                    # 1 = top 10% GLP-1 volume
    adopters = df["glp1_adopter"]
    df.loc[adopters, "glp1_decile"] = 10 - pd.qcut(df.loc[adopters, "glp1_claims"].rank(method="first"), 10, labels=False)
    df["diabetes_decile"] = 10 - pd.qcut(df["diabetes_total_claims"].rank(method="first"), 10, labels=False)
    df["glp1_decile"] = df["glp1_decile"].astype("Int64")

    HCP_360.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(HCP_360, index=False)
    return df
