"""CMS Open Payments, General Payments: industry payments to doctors (Lilly and Novo Nordisk, 2024–2025).

Why streaming? Each year's official CSV is ~8 GB (15M+ payments), and the web API is too slow for
~2M rows (10–40 s per 500-row page). So we read the official CSV *as it downloads*, keep only
Lilly / Novo Nordisk rows, and never store the full file on disk.

Run from the command line (~30 min per year):  python -m glp1_intel.data_collection.open_payments
"""
import re
import time

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from ..paths import RAW
from ._http import session

OUT_DIR = RAW / "open_payments_industry_to_doctor"
METASTORE = "https://openpaymentsdata.cms.gov/api/1/metastore/schemas/dataset/items"
YEARS = [2024, 2025]
MFR = "Applicable_Manufacturer_or_Applicable_GPO_Making_Payment_Name"
# Each company reports under several legal entities (e.g. "Lilly USA, LLC", "Eli Lilly and Company")
MFR_PATTERN = r"lilly|novo nordisk"
COLUMNS = [
    "Record_ID", "Program_Year", "Covered_Recipient_Type", "Covered_Recipient_NPI", "Covered_Recipient_Specialty_1",
    "Recipient_City", "Recipient_State", "Recipient_Zip_Code", MFR, "Total_Amount_of_Payment_USDollars",
    "Date_of_Payment", "Number_of_Payments_Included_in_Total_Amount", "Form_of_Payment_or_Transfer_of_Value",
    "Nature_of_Payment_or_Transfer_of_Value", "Related_Product_Indicator",
    "Name_of_Drug_or_Biological_or_Device_or_Medical_Supply_1", "Product_Category_or_Therapeutic_Area_1",
    "Name_of_Drug_or_Biological_or_Device_or_Medical_Supply_2",
    "Name_of_Drug_or_Biological_or_Device_or_Medical_Supply_3",
]


def download_urls() -> dict:
    """{year: official CSV URL} from the Open Payments catalogue."""
    items = session().get(METASTORE, params={"show-reference-ids": "false"}, timeout=120).json()
    urls = {}
    for d in items:
        if re.match(r"^\d{4} General Payment Data", d["title"]):
            dist = d["distribution"][0]
            urls[int(d["title"][:4])] = dist.get("downloadURL") or dist["data"]["downloadURL"]
    return urls


def fetch_year(year: int, url: str, overwrite: bool = False, chunksize: int = 250_000) -> dict:
    """Stream one year's CSV and write only Lilly / Novo Nordisk rows to Parquet."""
    out = OUT_DIR / f"open_payments_general_{year}_lilly_novo.parquet"
    if out.exists() and not overwrite:
        return {"year": year, "rows_kept": pq.ParquetFile(out).metadata.num_rows, "status": "already downloaded"}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    t, seen, kept, writer = time.time(), 0, 0, None
    with session().get(url, stream=True, timeout=600) as r:
        r.raise_for_status()
        r.raw.decode_content = True
        reader = pd.read_csv(r.raw, usecols=COLUMNS, dtype="string", chunksize=chunksize, low_memory=False)
        for chunk in reader:
            seen += len(chunk)
            keep = chunk[chunk[MFR].str.contains(MFR_PATTERN, case=False, na=False)]
            kept += len(keep)
            table = pa.Table.from_pandas(keep[COLUMNS], preserve_index=False)
            writer = writer or pq.ParquetWriter(tmp, table.schema, compression="zstd")
            writer.write_table(table)
            if seen % 2_000_000 < chunksize:
                print(f"  {year}: {seen:,} rows read, {kept:,} kept ({time.time() - t:.0f}s)", flush=True)
    writer.close()
    tmp.replace(out)                       # write-then-rename: a crash never leaves a half-written file
    return {"year": year, "rows_read": seen, "rows_kept": kept, "seconds": round(time.time() - t), "url": url}


def fetch(years=YEARS, overwrite: bool = False) -> pd.DataFrame:
    urls = download_urls()
    summary = [fetch_year(y, urls[y], overwrite) for y in years]
    df = pd.DataFrame(summary)
    df.to_csv(OUT_DIR / "download_summary.csv", index=False)
    return df


if __name__ == "__main__":
    print(fetch())
