"""NPPES NPI Registry: doctor details (credential, sex, practice ZIP, taxonomy) for our GLP-1 prescribers.

Source: the monthly full replacement file from https://download.cms.gov/nppes/NPI_Files.html (~1.2 GB zip,
~11 GB unzipped). The API allows one doctor per request (~5/s → ~11 hours for 200k doctors), so instead
we stream the main CSV *inside* the zip (never unzipped to disk) and keep only NPIs in our Part D subset.
"""
import zipfile

import duckdb
import pandas as pd

from ..paths import INTERIM, PART_D_2024_GLP1, RAW

RAW_DIR = RAW / "nppes_doctor_registry"
OUT = INTERIM / "nppes_glp1_prescribers.parquet"

# Column names in the NPPES file → our short names
COLUMNS = {
    "NPI": "npi",
    "Entity Type Code": "entity_type",                 # 1 = individual, 2 = organisation
    "Provider Credential Text": "credential",
    "Provider Sex Code": "sex",
    "Provider Business Practice Location Address City Name": "practice_city",
    "Provider Business Practice Location Address State Name": "practice_state",
    "Provider Business Practice Location Address Postal Code": "practice_zip",
    "Provider Enumeration Date": "enumeration_date",
    "Last Update Date": "last_update_date",
    "NPI Deactivation Date": "deactivation_date",
    **{f"Healthcare Provider Taxonomy Code_{i}": f"taxonomy_{i}" for i in range(1, 4)},
    **{f"Healthcare Provider Primary Taxonomy Switch_{i}": f"taxonomy_primary_{i}" for i in range(1, 4)},
}


def _main_csv(zf: zipfile.ZipFile) -> str:
    """The big provider file is named like npidata_pfile_20050523-20261012.csv (skip the *_fileheader.csv)."""
    return next(n for n in zf.namelist() if n.startswith("npidata_pfile") and not n.endswith("fileheader.csv"))


def build(zip_path=None, overwrite: bool = False, chunksize: int = 500_000) -> pd.DataFrame:
    if OUT.exists() and not overwrite:
        return pd.read_parquet(OUT)
    zip_path = zip_path or max(RAW_DIR.glob("NPPES_Data_Dissemination_*.zip"))
    wanted = set(duckdb.sql(f"SELECT DISTINCT Prscrbr_NPI FROM read_parquet('{PART_D_2024_GLP1.as_posix()}')")
                 .df()["Prscrbr_NPI"])
    kept = []
    with zipfile.ZipFile(zip_path) as zf, zf.open(_main_csv(zf)) as f:
        header = pd.read_csv(zf.open(_main_csv(zf)), nrows=0).columns
        # Sex column was renamed in newer files; take whichever exists
        cols = {c: v for c, v in COLUMNS.items() if c in header}
        if "Provider Sex Code" not in header:
            sex_col = next((c for c in header if "Sex" in c or "Gender" in c), None)
            if sex_col:
                cols[sex_col] = "sex"
        for chunk in pd.read_csv(f, usecols=list(cols), dtype=str, chunksize=chunksize):
            kept.append(chunk[chunk["NPI"].isin(wanted)])
    df = pd.concat(kept, ignore_index=True).rename(columns=cols)
    df["practice_zip5"] = df["practice_zip"].str[:5]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT, index=False)
    return df
