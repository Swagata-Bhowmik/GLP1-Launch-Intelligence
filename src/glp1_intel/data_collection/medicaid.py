"""Medicaid State Drug Utilization Data (SDUD): prescriptions per state, quarter and NDC.

Docs: https://data.medicaid.gov  (DKAN datastore API). Product names are truncated to 10 characters
and padded with spaces, so we match with LIKE 'BRAND%'.
Note: rows with state = 'XX' are national totals; drop them before summing states.
"""
import time

import pandas as pd

from ..paths import RAW
from ._http import session

SEARCH_URL = "https://data.medicaid.gov/api/1/search"
OUT_DIR = RAW / "medicaid_state_drug_utilization"
YEARS = [2024, 2025, 2026]
BRANDS = ["MOUNJARO", "ZEPBOUND", "FOUNDAYO", "OZEMPIC", "WEGOVY", "RYBELSUS", "TRULICITY",
          "VICTOZA", "SAXENDA", "LIRAGLUTID", "BYDUREON", "BYETTA", "XULTOPHY"]
PAGE = 500


def dataset_id(year: int, s=None) -> str:
    s = s or session()
    j = s.get(SEARCH_URL, params={"fulltext": f"State Drug Utilization Data {year}", "page-size": 5}, timeout=60).json()
    for d in j["results"].values():
        if d["title"].strip() == f"State Drug Utilization Data {year}":
            return d["identifier"]
    raise LookupError(f"SDUD {year} dataset not found")


def fetch_year(year: int, overwrite: bool = False) -> pd.DataFrame:
    out = OUT_DIR / f"sdud_{year}_glp1.csv"
    if out.exists() and not overwrite:
        return pd.read_csv(out, dtype=str)
    s = session()
    url = f"https://data.medicaid.gov/api/1/datastore/query/{dataset_id(year, s)}/0"
    rows = []
    for brand in BRANDS:
        offset = 0
        while True:
            j = s.get(url, params={"limit": PAGE, "offset": offset, "count": "false", "schema": "false",
                                   "conditions[0][property]": "product_name", "conditions[0][value]": f"{brand}%",
                                   "conditions[0][operator]": "like"}, timeout=180).json()
            batch = j.get("results", [])
            rows += batch
            if len(batch) < PAGE:
                break
            offset += PAGE
            time.sleep(0.2)
    df = pd.DataFrame(rows)
    if len(df):
        df["product_name"] = df["product_name"].str.strip()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    return df


def fetch_all(overwrite: bool = False) -> dict:
    return {y: len(fetch_year(y, overwrite)) for y in YEARS}
