"""CMS Open Payments, General Payments: industry payments to doctors (Lilly and Novo Nordisk, 2024–2025).

Why streaming? Each year's official CSV is ~8 GB (15M+ payments), and the web API is too slow for
~2M rows (10–40 s per 500-row page). So we read the official CSV *as it downloads*, keep only
Lilly / Novo Nordisk rows, and never store the full file on disk.

Why checkpoints? A 2-hour download will sometimes be interrupted. Every 1M rows we save a finished
part file plus the exact **byte offset** reached. A restart asks the server for the file *from that
byte* (HTTP Range request), so no work is repeated.

Run from the command line (~1.5–2 h per year, resumable):  python -m glp1_intel.data_collection.open_payments
"""
import csv
import io
import json
import re
import time

import pandas as pd
import pyarrow.parquet as pq

from ..paths import RAW
from ._http import session

OUT_DIR = RAW / "open_payments_industry_to_doctor"
METASTORE = "https://openpaymentsdata.cms.gov/api/1/metastore/schemas/dataset/items"
YEARS = [2024, 2025]
MFR = "Applicable_Manufacturer_or_Applicable_GPO_Making_Payment_Name"
# Each company reports under several legal entities (e.g. "Lilly USA, LLC", "Eli Lilly and Company")
MFR_PATTERN = re.compile(r"lilly|novo nordisk", re.IGNORECASE)
COLUMNS = [
    "Record_ID", "Program_Year", "Covered_Recipient_Type", "Covered_Recipient_NPI", "Covered_Recipient_Specialty_1",
    "Recipient_City", "Recipient_State", "Recipient_Zip_Code", MFR, "Total_Amount_of_Payment_USDollars",
    "Date_of_Payment", "Number_of_Payments_Included_in_Total_Amount", "Form_of_Payment_or_Transfer_of_Value",
    "Nature_of_Payment_or_Transfer_of_Value", "Related_Product_Indicator",
    "Name_of_Drug_or_Biological_or_Device_or_Medical_Supply_1", "Product_Category_or_Therapeutic_Area_1",
    "Name_of_Drug_or_Biological_or_Device_or_Medical_Supply_2",
    "Name_of_Drug_or_Biological_or_Device_or_Medical_Supply_3",
]
ROWS_PER_PART = 1_000_000


def download_urls() -> dict:
    """{year: official CSV URL} from the Open Payments catalogue."""
    items = session().get(METASTORE, params={"show-reference-ids": "false"}, timeout=120).json()
    urls = {}
    for d in items:
        if re.match(r"^\d{4} General Payment Data", d["title"]):
            dist = d["distribution"][0]
            urls[int(d["title"][:4])] = dist.get("downloadURL") or dist["data"]["downloadURL"]
    return urls


def _byte_lines(chunks):
    """Split a stream of byte chunks into lines, *keeping* each trailing newline so byte counts stay exact."""
    rest = b""
    for chunk in chunks:
        rest += chunk
        *lines, rest = rest.split(b"\n")
        for line in lines:
            yield line + b"\n"
    if rest:
        yield rest


def _records(byte_lines):
    """Yield (row, byte_offset_after_row) from an iterator of raw byte lines.

    csv.reader handles quoted fields that contain newlines, so a "record" may span several lines;
    we only report an offset when a full record has been consumed (= a safe restart point).
    """
    consumed = 0

    def text_lines():
        nonlocal consumed
        for line in byte_lines:
            consumed += len(line)
            yield line.decode("utf-8", errors="replace")

    for row in csv.reader(text_lines()):
        yield row, consumed


def fetch_year(year: int, url: str) -> dict:
    """Stream one year (resuming from the last checkpoint) and write Lilly / Novo rows to Parquet."""
    out = OUT_DIR / f"open_payments_general_{year}_lilly_novo.parquet"
    if out.exists():
        return {"year": year, "rows_kept": pq.ParquetFile(out).metadata.num_rows, "status": "already downloaded"}
    work = OUT_DIR / f"_parts_{year}"
    work.mkdir(parents=True, exist_ok=True)
    ckpt_file = work / "checkpoint.json"
    ckpt = json.loads(ckpt_file.read_text()) if ckpt_file.exists() else {"offset": None, "rows_read": 0, "kept": 0, "part": 0}

    s = session()
    # ── Header (always from byte 0) ─────────────────────────────────────────
    with s.get(url, headers={"Range": "bytes=0-65535"}, stream=True, timeout=120) as r:
        first = next(r.iter_lines(delimiter=b"\n"))
    header = next(csv.reader(io.StringIO(first.decode("utf-8-sig"))))
    header_bytes = len(first) + 1
    idx = [header.index(c) for c in COLUMNS]
    mfr_i = header.index(MFR)
    start = ckpt["offset"] or header_bytes

    t0, buf = time.time(), []
    print(f"{year}: starting at byte {start:,} (rows already read: {ckpt['rows_read']:,})", flush=True)

    def flush(offset):
        """Write the buffered rows as a part file, then save the checkpoint (in that order)."""
        nonlocal buf
        pd.DataFrame(buf, columns=COLUMNS).astype("string").to_parquet(work / f"part_{ckpt['part']:04d}.parquet", index=False)
        ckpt.update(offset=offset, part=ckpt["part"] + 1)
        ckpt_file.write_text(json.dumps(ckpt))
        buf = []
        print(f"  {year}: {ckpt['rows_read']:,} rows read, {ckpt['kept']:,} kept ({time.time() - t0:.0f}s)", flush=True)

    with s.get(url, headers={"Range": f"bytes={start}-"}, stream=True, timeout=600) as r:
        r.raise_for_status()
        since_flush = 0
        for row, consumed in _records(_byte_lines(r.iter_content(chunk_size=1 << 20))):
            if len(row) < len(header):            # blank / malformed trailing line
                continue
            ckpt["rows_read"] += 1
            since_flush += 1
            if MFR_PATTERN.search(row[mfr_i]):
                buf.append([row[i] for i in idx])
                ckpt["kept"] += 1
            if since_flush >= ROWS_PER_PART:
                flush(start + consumed)
                since_flush = 0
        flush(None)                                # final part; offset no longer needed

    # ── Combine parts into the final file, then clean up ────────────────────
    parts = sorted(work.glob("part_*.parquet"))
    pd.concat(pd.read_parquet(p) for p in parts).drop_duplicates("Record_ID").to_parquet(out, index=False)
    for p in parts:
        p.unlink()
    ckpt_file.unlink()
    work.rmdir()
    return {"year": year, "rows_read": ckpt["rows_read"], "rows_kept": pq.ParquetFile(out).metadata.num_rows,
            "minutes": round((time.time() - t0) / 60)}


def fetch(years=YEARS) -> pd.DataFrame:
    urls = download_urls()
    summary = [fetch_year(y, urls[y]) for y in years]
    df = pd.DataFrame(summary)
    df.to_csv(OUT_DIR / "download_summary.csv", index=False)
    return df


if __name__ == "__main__":
    print(fetch())
