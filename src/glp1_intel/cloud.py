"""Running the app on a small free server (Streamlit Community Cloud).

- `ensure_assets()` downloads what Git does not hold: the app's data tables (a Hugging Face dataset repo) and the three
  fine-tuned models (Hugging Face model repos). Files already on disk are never downloaded again.
- `LIGHT` is True on machines with < 8 GB RAM (or GLP1_LIGHT=1): the live-LLM buttons are switched off and the note
  models load in bfloat16, which halves their memory (~1.9 GB → ~1 GB).
"""
import os

from glp1_intel.paths import ROOT

OWNER = os.getenv("HF_MODEL_OWNER", "SwagataBhowmik")
DATA_REPO = f"{OWNER}/glp1-launch-intelligence-data"
MODEL_REPOS = {"visit_note_ner_biomedbert": "glp1-visit-note-ner-biomedbert",
               "ade_sentence_biomedbert": "glp1-ade-sentence-biomedbert",
               "visit_note_ae_mode_bert": "glp1-visit-note-ae-mode-bert"}

# Files the app reads that are git-ignored (published to DATA_REPO by deploy/publish.py)
DATA_FILES = ["app/data", "data/03_processed/kb_chunks.parquet", "data/03_processed/targeting_scores.parquet",
              "data/02_interim/kb_emb_bge.npy", "data/02_interim/kb_emb_bge_ids.txt",
              "data/02_interim/kb_emb_minilm.npy", "data/02_interim/kb_emb_minilm_ids.txt",
              "data/01_raw/fda_drug_labels", "data/01_raw/fda_faers_side_effect_reports/faers_counts_glp1.csv"]


def _total_ram() -> float:
    try:
        import psutil
        return psutil.virtual_memory().total
    except Exception:
        return 16e9


LIGHT = os.getenv("GLP1_LIGHT") == "1" or _total_ram() < 8e9


def ensure_assets() -> list[str]:
    """Download missing data and models; returns what was fetched (empty on a fully set-up machine)."""
    from huggingface_hub import snapshot_download
    fetched = []
    if not (ROOT / "app" / "data" / "kpis.json").exists():
        snapshot_download(DATA_REPO, repo_type="dataset", local_dir=ROOT)
        fetched.append("data")
    for local, repo in MODEL_REPOS.items():
        out = ROOT / "models" / local
        if not (out / "config.json").exists():
            try:
                snapshot_download(f"{OWNER}/{repo}", local_dir=out)
                fetched.append(local)
            except Exception as e:          # the note page reports missing models; the rest of the app still runs
                print("could not download", repo, "->", e, flush=True)
    return fetched
