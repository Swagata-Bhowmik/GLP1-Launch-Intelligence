"""Link PubMed authors and ClinicalTrials.gov investigators to HCP 360 doctors (NPI).

Neither source has an NPI, so this is **entity resolution** by name:
    key = (LAST NAME, FIRST INITIAL, STATE)
A link is kept only if exactly **one** doctor in HCP 360 has that key (precision over recall:
a wrong link would put the wrong doctor's research in a pre-visit brief). Ambiguous and unmatched
names are counted and reported, so the match quality is visible.
"""
import json
import re
import unicodedata

import pandas as pd

from ..paths import INTERIM, RAW

STATES = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA", "Colorado": "CO",
    "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA",
    "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI",
    "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY", "North Carolina": "NC",
    "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI",
    "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT",
    "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
    "Puerto Rico": "PR",
}
ABBR = set(STATES.values())
# "…, Houston, TX 77030, USA"  or  "…, Boston, MA, USA"
STATE_ZIP = re.compile(r",\s*([A-Z]{2})\s*(?:\d{5})?(?:-\d{4})?\s*,?\s*(?:USA|United States)")
STATE_NAME = re.compile(r"\b(" + "|".join(sorted(STATES, key=len, reverse=True)) + r")\b")

PUBMED_OUT = INTERIM / "pubmed_author_npi_links.parquet"
TRIALS_OUT = INTERIM / "trial_investigator_npi_links.parquet"


def _norm(s: str) -> str:
    """Upper-case, strip accents and punctuation: 'García-López' → 'GARCIALOPEZ'."""
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z]", "", s.upper())


def state_from_affiliation(aff: str) -> str | None:
    """US state from an affiliation string, or None if it is not clearly a US address."""
    if not aff or not re.search(r"USA|United States", aff):
        return None
    m = STATE_ZIP.search(aff)
    if m and m.group(1) in ABBR:
        return m.group(1)
    m = STATE_NAME.search(aff)
    return STATES[m.group(1)] if m else None


def _key_index(hcp: pd.DataFrame) -> pd.DataFrame:
    """(last, initial, state) → npi, keeping only keys that identify exactly one doctor."""
    k = pd.DataFrame({
        "last": hcp["last_name"].map(_norm),
        "initial": hcp["first_name"].fillna("").map(_norm).str[:1],
        "state": hcp["state"],
        "npi": hcp["npi"],
    })
    counts = k.groupby(["last", "initial", "state"])["npi"].transform("count")
    return k.assign(n_candidates=counts)


def _match(names: pd.DataFrame, idx: pd.DataFrame) -> pd.DataFrame:
    """Left-join names onto the key index and label each as matched / ambiguous / not found."""
    m = names.merge(idx, on=["last", "initial", "state"], how="left")
    m["match"] = "not found"
    m.loc[m["n_candidates"] == 1, "match"] = "matched"
    m.loc[m["n_candidates"] > 1, "match"] = "ambiguous"
    # ambiguous keys produced several rows per name: keep one row for counting, no NPI
    m.loc[m["match"] != "matched", "npi"] = None
    return m.drop_duplicates(subset=[c for c in names.columns] + ["match"])


def pubmed_links(hcp: pd.DataFrame, overwrite: bool = False) -> pd.DataFrame:
    """One row per (paper, US author) with the matched NPI where unique."""
    if PUBMED_OUT.exists() and not overwrite:
        return pd.read_parquet(PUBMED_OUT)
    rows = []
    for f in sorted((RAW / "pubmed_research_papers").glob("pubmed_*.jsonl")):
        for line in f.open(encoding="utf-8"):
            p = json.loads(line)
            for pos, a in enumerate(p["authors"]):
                state = next((s for s in map(state_from_affiliation, a["affiliations"]) if s), None)
                if state and a["last"]:
                    rows.append({"pmid": p["pmid"], "year": p["year"], "query": p["query"], "title": p["title"],
                                 "author_position": "first" if pos == 0 else "last" if pos == len(p["authors"]) - 1 else "middle",
                                 "last": _norm(a["last"]), "initial": _norm(a["first"])[:1], "state": state})
    names = pd.DataFrame(rows).drop_duplicates(["pmid", "last", "initial", "state"])
    out = _match(names, _key_index(hcp))
    out.to_parquet(PUBMED_OUT, index=False)
    return out


def _split_name(full: str) -> tuple[str, str]:
    """'Jane A. Smith, MD, PhD' → ('SMITH', 'J')."""
    name = re.split(r",", full or "")[0]
    name = re.sub(r"\b(Dr|MD|DO|PhD|Prof)\.?\b", "", name, flags=re.I).strip()
    parts = [p for p in name.split() if re.search(r"[A-Za-z]", p)]
    if len(parts) < 2:
        return "", ""
    return _norm(parts[-1]), _norm(parts[0])[:1]


def trial_links(hcp: pd.DataFrame, overwrite: bool = False) -> pd.DataFrame:
    """One row per (study, US investigator) from site contacts and overall officials."""
    if TRIALS_OUT.exists() and not overwrite:
        return pd.read_parquet(TRIALS_OUT)
    rows = []
    for f in sorted((RAW / "clinicaltrials_gov_studies").glob("ctgov_*.jsonl")):
        drug = f.stem.replace("ctgov_", "")
        for line in f.open(encoding="utf-8"):
            ps = json.loads(line)["protocolSection"]
            nct = ps["identificationModule"]["nctId"]
            sponsor = ps["sponsorCollaboratorsModule"]["leadSponsor"]["name"]
            cl = ps.get("contactsLocationsModule", {})
            for loc in cl.get("locations", []) or []:
                if loc.get("country") != "United States" or loc.get("state") not in STATES:
                    continue
                for c in loc.get("contacts", []) or []:
                    if c.get("role") in ("PRINCIPAL_INVESTIGATOR", "SUB_INVESTIGATOR"):
                        last, ini = _split_name(c.get("name", ""))
                        rows.append({"nct_id": nct, "drug": drug, "sponsor": sponsor, "role": c["role"],
                                     "last": last, "initial": ini, "state": STATES[loc["state"]]})
            for o in cl.get("overallOfficials", []) or []:
                state = state_from_affiliation(o.get("affiliation", "") + ", USA")
                last, ini = _split_name(o.get("name", ""))
                if state:
                    rows.append({"nct_id": nct, "drug": drug, "sponsor": sponsor, "role": o.get("role", "OFFICIAL"),
                                 "last": last, "initial": ini, "state": state})
    names = pd.DataFrame(rows)
    names = names[names["last"] != ""].drop_duplicates(["nct_id", "last", "initial", "state"])
    out = _match(names, _key_index(hcp))
    out.to_parquet(TRIALS_OUT, index=False)
    return out


def match_summary(links: pd.DataFrame, source: str) -> pd.DataFrame:
    s = links["match"].value_counts().rename_axis("match").reset_index(name="names")
    s["pct"] = (100 * s["names"] / s["names"].sum()).round(1)
    return s.assign(source=source)[["source", "match", "names", "pct"]]


def npi_features(pub: pd.DataFrame, trials: pd.DataFrame) -> pd.DataFrame:
    """Per-NPI research signals for the targeting score."""
    p = pub[pub["match"] == "matched"]
    t = trials[trials["match"] == "matched"]
    pf = p.groupby("npi").agg(pubmed_papers=("pmid", "nunique"),
                              pubmed_senior_author=("author_position", lambda s: (s != "middle").sum()))
    tf = t.groupby("npi").agg(trials=("nct_id", "nunique"),
                              trials_tirzepatide_or_orfor=("drug", lambda s: s.isin(["tirzepatide", "orforglipron"]).sum()))
    return pf.join(tf, how="outer").fillna(0).astype(int).reset_index()
