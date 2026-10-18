"""ClinicalTrials.gov API v2: GLP-1 studies with sponsors, sites and investigators.

Docs: https://clinicaltrials.gov/data-api/api  ·  Paging uses `nextPageToken`.
"""
import json
import time

from ..paths import RAW
from ._http import session

URL = "https://clinicaltrials.gov/api/v2/studies"
OUT_DIR = RAW / "clinicaltrials_gov_studies"
INTERVENTIONS = ["orforglipron", "tirzepatide", "semaglutide", "dulaglutide", "liraglutide", "retatrutide", "cagrilintide"]


def fetch_intervention(drug: str, overwrite: bool = False) -> int:
    """All studies whose intervention mentions `drug`; full study JSON, one per line."""
    out = OUT_DIR / f"ctgov_{drug}.jsonl"
    if out.exists() and not overwrite:
        return sum(1 for _ in out.open(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    s, token, n = session(), None, 0
    with out.open("w", encoding="utf-8") as f:
        while True:
            params = {"query.intr": drug, "pageSize": 1000, "format": "json", **({"pageToken": token} if token else {})}
            j = s.get(URL, params=params, timeout=120).json()
            for study in j.get("studies", []):
                f.write(json.dumps(study, ensure_ascii=False) + "\n")
                n += 1
            token = j.get("nextPageToken")
            if not token:
                break
            time.sleep(0.5)
    return n


def fetch_all(overwrite: bool = False) -> dict:
    return {d: fetch_intervention(d, overwrite) for d in INTERVENTIONS}
