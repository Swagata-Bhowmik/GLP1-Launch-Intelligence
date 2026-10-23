"""Space start-up: download the three fine-tuned models from the Hugging Face Hub into models/ (skipped if present)."""
import os
from pathlib import Path

from huggingface_hub import snapshot_download

ROOT = Path(__file__).resolve().parents[1]
OWNER = os.getenv("HF_MODEL_OWNER", "SwagataBhowmik")
MODELS = {"visit_note_ner_biomedbert": "glp1-visit-note-ner-biomedbert",
          "ade_sentence_biomedbert": "glp1-ade-sentence-biomedbert",
          "visit_note_ae_mode_bert": "glp1-visit-note-ae-mode-bert"}

for local, repo in MODELS.items():
    out = ROOT / "models" / local
    if (out / "config.json").exists():
        continue
    try:
        snapshot_download(f"{OWNER}/{repo}", local_dir=out)
        print("downloaded", repo, flush=True)
    except Exception as e:                      # the app still runs; the note page shows which models are missing
        print("could not download", repo, "->", e, flush=True)
