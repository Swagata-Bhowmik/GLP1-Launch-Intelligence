"""openFDA: FAERS side-effect report counts and drug label text.

Docs: https://open.fda.gov/apis/  ·  Without an API key: 240 requests/minute, 1,000/day.
Set OPENFDA_API_KEY in .env to raise the limit (optional).
"""
import json
import os
import time

import pandas as pd

from ..paths import RAW
from ._http import session

EVENT_URL = "https://api.fda.gov/drug/event.json"
LABEL_URL = "https://api.fda.gov/drug/label.json"
FAERS_DIR = RAW / "fda_faers_side_effect_reports"
LABEL_DIR = RAW / "fda_drug_labels"

# openFDA maps most drugs to a generic name; brand-new drugs (orforglipron) may only appear as free-text product names
FAERS_DRUG_SEARCH = {
    "tirzepatide": 'patient.drug.openfda.generic_name:"tirzepatide"',
    "semaglutide": 'patient.drug.openfda.generic_name:"semaglutide"',
    "dulaglutide": 'patient.drug.openfda.generic_name:"dulaglutide"',
    "liraglutide": 'patient.drug.openfda.generic_name:"liraglutide"',
    "exenatide": 'patient.drug.openfda.generic_name:"exenatide"',
    "orforglipron": '(patient.drug.openfda.generic_name:"orforglipron" OR patient.drug.medicinalproduct:"orforglipron" '
                    'OR patient.drug.medicinalproduct:"foundayo")',
}

# What to count for each drug: (output name, openFDA field, max buckets).
# Without an API key openFDA allows at most 100 buckets per count request.
FAERS_COUNTS = [
    ("reactions", "patient.reaction.reactionmeddrapt.exact", 100),
    ("serious", "serious", 10),
    ("sex", "patient.patientsex", 10),
    ("reporter", "primarysource.qualification", 10),
    ("product_names", "patient.drug.medicinalproduct.exact", 100),
]

QUARTERS = [(y, q) for y in range(2022, 2027) for q in range(1, 5) if (y, q) <= (2026, 2)]
QUARTER_RANGES = {1: ("0101", "0331"), 2: ("0401", "0630"), 3: ("0701", "0930"), 4: ("1001", "1231")}

LABEL_BRANDS = ["Mounjaro", "Zepbound", "Foundayo", "Ozempic", "Wegovy", "Rybelsus", "Trulicity", "Victoza", "Saxenda"]


def _params(extra: dict) -> dict:
    key = os.getenv("OPENFDA_API_KEY")
    return {**extra, **({"api_key": key} if key else {})}


def fetch_faers_counts(overwrite: bool = False) -> pd.DataFrame:
    """Aggregated FAERS counts per drug. Returns one tidy table: drug, count_type, term, count.

    We use openFDA's server-side `count=` instead of downloading millions of individual reports.
    """
    out = FAERS_DIR / "faers_counts_glp1.csv"
    if out.exists() and not overwrite:
        return pd.read_csv(out, dtype={"term": str})
    s, rows, totals = session(), [], {}
    for drug, search in FAERS_DRUG_SEARCH.items():
        r = s.get(EVENT_URL, params=_params({"search": search, "limit": 1}), timeout=60)
        totals[drug] = r.json()["meta"]["results"]["total"] if r.status_code == 200 else 0
        if not totals[drug]:
            continue
        for name, field, limit in FAERS_COUNTS:
            r = s.get(EVENT_URL, params=_params({"search": search, "count": field, "limit": limit}), timeout=60)
            if r.status_code == 404:          # openFDA answers 404 when nothing matches
                continue
            r.raise_for_status()
            rows += [{"drug": drug, "count_type": name, "term": str(x["term"]), "count": x["count"]}
                     for x in r.json()["results"]]
            time.sleep(0.3)                   # stay well under 240 requests/minute
        # Reports received per quarter: one small "total" request per quarter
        for y, q in QUARTERS:
            start, end = QUARTER_RANGES[q]
            r = s.get(EVENT_URL, params=_params({"search": f"{search} AND receivedate:[{y}{start} TO {y}{end}]",
                                                  "limit": 1}), timeout=60)
            n = r.json()["meta"]["results"]["total"] if r.status_code == 200 else 0
            rows.append({"drug": drug, "count_type": "reports_per_quarter", "term": f"{y}Q{q}", "count": n})
            time.sleep(0.3)
    df = pd.DataFrame(rows)
    FAERS_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    meta = {"fetched_at": time.strftime("%Y-%m-%d"), "total_reports": totals, "search": FAERS_DRUG_SEARCH}
    (FAERS_DIR / "faers_meta.json").write_text(json.dumps(meta, indent=2))
    return df


def fetch_labels(overwrite: bool = False) -> dict:
    """Full structured product label (SPL) JSON for each GLP-1 brand; one file per brand."""
    LABEL_DIR.mkdir(parents=True, exist_ok=True)
    s, found = session(), {}
    for brand in LABEL_BRANDS:
        out = LABEL_DIR / f"label_{brand.lower()}.json"
        if out.exists() and not overwrite:
            found[brand] = len(json.loads(out.read_text(encoding="utf-8")))
            continue
        r = s.get(LABEL_URL, params=_params({"search": f'openfda.brand_name:"{brand}"', "limit": 20}), timeout=60)
        results = r.json().get("results", []) if r.status_code == 200 else []
        out.write_text(json.dumps(results, indent=1), encoding="utf-8")
        found[brand] = len(results)
        time.sleep(0.3)
    return found
