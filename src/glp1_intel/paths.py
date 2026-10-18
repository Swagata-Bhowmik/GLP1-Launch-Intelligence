"""Project paths, so every module and notebook writes to the same places."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "01_raw"
INTERIM = DATA / "02_interim"
PROCESSED = DATA / "03_processed"

PART_D_2024_GLP1 = INTERIM / "part_d_2024_glp1.parquet"
