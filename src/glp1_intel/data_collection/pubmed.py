"""PubMed abstracts + authors via NCBI E-utilities (esearch → efetch).

Docs: https://www.ncbi.nlm.nih.gov/books/NBK25499/  ·  Limit: 3 requests/second without an API key
(10/s with NCBI_API_KEY in .env).
"""
import json
import os
import time
import xml.etree.ElementTree as ET

import requests

from ..paths import RAW
from ._http import session

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
OUT_DIR = RAW / "pubmed_research_papers"

# name → (query, max papers). Most recent papers first.
QUERIES = {
    "orforglipron": ('orforglipron', 2000),
    "tirzepatide": ('tirzepatide AND 2022:2026[pdat]', 6000),
    "semaglutide_obesity_diabetes": ('semaglutide AND (obesity OR "weight loss" OR diabetes) AND 2024:2026[pdat]', 6000),
    "glp1_medicare_access": ('("GLP-1 receptor agonists" OR GLP-1) AND (Medicare OR coverage OR access OR adherence OR prescribing) '
                             'AND 2023:2026[pdat]', 3000),
}


def _key() -> dict:
    k = os.getenv("NCBI_API_KEY")
    return {"api_key": k} if k else {}


def _text(el) -> str:
    return "".join(el.itertext()).strip() if el is not None else ""


def parse_article(art: ET.Element) -> dict:
    """One PubmedArticle XML element → a flat dict (title, abstract, authors with affiliations, MeSH terms)."""
    cit = art.find("MedlineCitation")
    a = cit.find("Article")
    abstract = " ".join(
        (f"{p.get('Label')}: " if p.get("Label") else "") + _text(p) for p in a.findall("Abstract/AbstractText"))
    authors = []
    for au in a.findall("AuthorList/Author"):
        authors.append({
            "last": _text(au.find("LastName")), "first": _text(au.find("ForeName")),
            "affiliations": [_text(x) for x in au.findall("AffiliationInfo/Affiliation")],
        })
    year = _text(a.find("Journal/JournalIssue/PubDate/Year")) or _text(a.find("Journal/JournalIssue/PubDate/MedlineDate"))[:4]
    return {
        "pmid": _text(cit.find("PMID")),
        "title": _text(a.find("ArticleTitle")),
        "abstract": abstract,
        "journal": _text(a.find("Journal/Title")),
        "year": year,
        "pub_types": [_text(x) for x in a.findall("PublicationTypeList/PublicationType")],
        "mesh": [_text(x.find("DescriptorName")) for x in cit.findall("MeshHeadingList/MeshHeading")],
        "authors": authors,
    }


def _get_with_retry(s, url: str, params: dict, tries: int = 5) -> requests.Response:
    """GET that also retries dropped connections mid-download (urllib3's Retry only covers HTTP status codes)."""
    for attempt in range(tries):
        try:
            r = s.get(url, params=params, timeout=120)
            r.raise_for_status()
            return r
        except (requests.ConnectionError, requests.exceptions.ChunkedEncodingError, requests.Timeout):
            if attempt == tries - 1:
                raise
            time.sleep(2 ** attempt)


def fetch_query(name: str, term: str, max_n: int, overwrite: bool = False, batch: int = 200) -> int:
    """Search PubMed, then download records in batches using the NCBI history server. Writes JSONL."""
    out = OUT_DIR / f"pubmed_{name}.jsonl"
    if out.exists() and not overwrite:
        return sum(1 for _ in out.open(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    s = session()
    r = s.get(f"{BASE}/esearch.fcgi", params={"db": "pubmed", "term": term, "usehistory": "y", "retmode": "json",
                                              "retmax": 0, "sort": "pub_date", **_key()}, timeout=60)
    res = r.json()["esearchresult"]
    total, webenv, qkey = int(res["count"]), res["webenv"], res["querykey"]
    n = min(total, max_n)
    written = 0
    tmp = out.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for start in range(0, n, batch):
            r = _get_with_retry(s, f"{BASE}/efetch.fcgi", {"db": "pubmed", "WebEnv": webenv, "query_key": qkey,
                                                           "retstart": start, "retmax": min(batch, n - start),
                                                           "retmode": "xml", **_key()})
            for art in ET.fromstring(r.content).findall("PubmedArticle"):
                rec = parse_article(art)
                rec["query"] = name
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                written += 1
            time.sleep(0.4)
    tmp.replace(out)                       # only a complete download gets the final name
    (OUT_DIR / f"pubmed_{name}_meta.json").write_text(json.dumps(
        {"term": term, "total_matches": total, "downloaded": written, "fetched_at": time.strftime("%Y-%m-%d")}, indent=2))
    return written


def fetch_all(overwrite: bool = False) -> dict:
    return {name: fetch_query(name, term, n, overwrite) for name, (term, n) in QUERIES.items()}
