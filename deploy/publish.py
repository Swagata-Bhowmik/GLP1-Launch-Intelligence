"""Stage and publish the app to a Hugging Face Space, and the three fine-tuned models to model repos.

    python deploy/publish.py --stage-only        build deploy/_space/ (what the Space will contain) and stop
    python deploy/publish.py                     stage + upload models + create/update the Space

Needs HF_TOKEN (a *write* token) in .env. The token is read from the environment and never printed.
"""
import argparse
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "deploy" / "_space"
SPACE_NAME = "glp1-launch-intelligence"

# Everything the app reads at runtime (checked by running the staged copy locally)
COPY = [
    "app", ".streamlit", "src/glp1_intel", "pyproject.toml",
    "data/03_processed/kb_chunks.parquet", "data/03_processed/targeting_scores.parquet",
    "data/02_interim/kb_emb_bge.npy", "data/02_interim/kb_emb_bge_ids.txt",
    "data/02_interim/kb_emb_minilm.npy", "data/02_interim/kb_emb_minilm_ids.txt",
    "data/01_raw/fda_drug_labels", "data/01_raw/fda_faers_side_effect_reports/faers_counts_glp1.csv",
    "data/04_synthetic_visit_notes/visit_notes_v1.jsonl", "data/04_synthetic_visit_notes/DATASET_CARD.md",
    "reports/evaluation",
]
SKIP = shutil.ignore_patterns("__pycache__", "*.pyc", "*.csv~")

SPACE_README = """---
title: GLP-1 Launch Intelligence
emoji: 💊
colorFrom: purple
colorTo: green
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: Open pharma sales analytics + NLP, RAG and agents on public data
---

# GLP-1 Launch Intelligence

Open-source analytics for pharma sales-optimization teams after the 2026 GLP-1 market shift, on **real public US data**
(Medicare Part D 2024, NPPES, openFDA FAERS and labels, PubMed) plus a **synthetic** visit-notes dataset.

Pages: market · targeting · doctor 360 · safety signals · **pre-visit brief** · **visit-note analysis** · **Ask AI** (agent).

Code, notebooks and evaluation: https://github.com/Swagata-Bhowmik/GLP1-Launch-Intelligence

Independent portfolio project. Not affiliated with any pharmaceutical company. Not medical advice.
The free CPU server is slow for the live LLM features (several minutes per question); the evaluated examples are instant.
"""

MODEL_CARDS = {
    "visit_note_ner_biomedbert": ("glp1-visit-note-ner-biomedbert", "token-classification", """
Token classifier for GLP-1 sales-rep visit notes: tags **DRUG**, **ADVERSE_EVENT** and **DOSE** (BIO scheme).
Fine-tuned from `microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext` on the synthetic visit-notes dataset
(notebook 12). Test entity-level F1 **0.98** (DRUG 1.00, ADVERSE_EVENT 0.95, DOSE 0.62 on only 5 entities).
**Limits:** labels are lexicon-generated and the notes are synthetic, so real-world accuracy will be lower."""),
    "ade_sentence_biomedbert": ("glp1-ade-sentence-biomedbert", "text-classification", """
Sentence classifier: does the sentence describe an **adverse drug event**? Fine-tuned BiomedBERT on ADE Corpus v2
(deduplicated split, notebook 12). Test F1 **0.90** [0.89–0.92], PR-AUC 0.96; at the ≥90%-recall threshold (0.58)
precision 0.89 (TF-IDF baseline: 0.47). **Limits:** case-report English from older literature (domain shift);
use as a triage aid for human pharmacovigilance review, never as the decision."""),
    "visit_note_ae_mode_bert": ("glp1-visit-note-ae-mode-bert", "text-classification", """
Classifies how a visit note talks about side effects: **none / concern / reported / negated** (labels LABEL_0–3 in that order).
Fine-tuned `bert-base-uncased` on the synthetic visit-notes dataset (notebook 11). Test macro-F1 **0.97** [0.94–1.00].
**Limits:** synthetic training data; expect lower accuracy on real notes."""),
}


def stage() -> Path:
    if STAGE.exists():
        shutil.rmtree(STAGE)
    for rel in COPY:
        src, dst = ROOT / rel, STAGE / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst, ignore=SKIP) if src.is_dir() else shutil.copy2(src, dst)
    for f in ["Dockerfile", "requirements-space.txt"]:
        shutil.copy2(ROOT / "deploy" / f, STAGE / f)
    (STAGE / "deploy").mkdir(exist_ok=True)
    shutil.copy2(ROOT / "deploy" / "fetch_models.py", STAGE / "deploy" / "fetch_models.py")
    (STAGE / "README.md").write_text(SPACE_README, encoding="utf-8")
    (STAGE / ".gitattributes").write_text("*.parquet filter=lfs diff=lfs merge=lfs -text\n*.npy filter=lfs diff=lfs merge=lfs -text\n")
    size = sum(p.stat().st_size for p in STAGE.rglob("*") if p.is_file()) / 1e6
    print(f"staged {STAGE} ({size:.0f} MB)")
    return STAGE


def card(repo: str, task: str, body: str, owner: str) -> str:
    return (f"---\nlicense: mit\nlanguage: en\npipeline_tag: {task}\ntags: [biomedical, pharma, glp-1, portfolio]\n---\n"
            f"# {repo}\n{body.strip()}\n\nPart of [GLP-1 Launch Intelligence](https://github.com/Swagata-Bhowmik/GLP1-Launch-Intelligence) "
            f"by {owner}. Public and synthetic data only; not affiliated with any pharmaceutical company; not medical advice.\n")


DATA_README = """---
license: other
tags: [pharma, glp-1, medicare, portfolio]
---
# GLP-1 Launch Intelligence · app data

Small derived tables that the [GLP-1 Launch Intelligence](https://github.com/Swagata-Bhowmik/GLP1-Launch-Intelligence)
app downloads at start-up: aggregated Medicare Part D 2024 prescribing per doctor and targeting scores (public CMS data;
doctor names come from the public NPPES registry), FDA label sections (openFDA), FAERS report counts, and the retrieval
index (text chunks + sentence embeddings). Rebuilt by the project's notebooks 02–05 and 13.
Public data only; not affiliated with any pharmaceutical company; not medical advice.
"""

args_space_only_skip = True     # Docker Spaces now need a paid plan; the app is hosted on Streamlit Community Cloud


def publish() -> None:
    from dotenv import load_dotenv
    from huggingface_hub import HfApi
    load_dotenv(ROOT / ".env")
    token = os.getenv("HF_TOKEN")
    if not token:
        raise SystemExit("HF_TOKEN is missing from .env")
    api = HfApi(token=token)
    owner = api.whoami()["name"]
    print("logged in as", owner)
    for local, (repo, task, body) in (MODEL_CARDS.items() if os.getenv("SKIP_MODELS") != "1" else []):
        rid = f"{owner}/{repo}"
        api.create_repo(rid, repo_type="model", exist_ok=True)
        (ROOT / "models" / local / "README.md").write_text(card(repo, task, body, owner), encoding="utf-8")
        api.upload_folder(repo_id=rid, folder_path=ROOT / "models" / local, repo_type="model",
                          commit_message="Upload fine-tuned model and card")
        print("model uploaded:", f"https://huggingface.co/{rid}")
    data_repo = f"{owner}/glp1-launch-intelligence-data"
    api.create_repo(data_repo, repo_type="dataset", exist_ok=True)
    (STAGE / "DATA_README.md").write_text(DATA_README, encoding="utf-8")
    api.upload_file(path_or_fileobj=STAGE / "DATA_README.md", path_in_repo="README.md", repo_id=data_repo, repo_type="dataset")
    from glp1_intel.cloud import DATA_FILES
    for rel in DATA_FILES:
        src = STAGE / rel
        if src.is_dir():
            api.upload_folder(repo_id=data_repo, repo_type="dataset", folder_path=src, path_in_repo=rel)
        else:
            api.upload_file(path_or_fileobj=src, path_in_repo=rel, repo_id=data_repo, repo_type="dataset")
    print("data uploaded:", f"https://huggingface.co/datasets/{data_repo}")
    if args_space_only_skip:
        return
    sid = f"{owner}/{SPACE_NAME}"
    api.create_repo(sid, repo_type="space", space_sdk="docker", exist_ok=True)
    api.add_space_variable(sid, "HF_MODEL_OWNER", owner)
    api.upload_folder(repo_id=sid, folder_path=STAGE, repo_type="space", commit_message="Deploy app")
    print("space:", f"https://huggingface.co/spaces/{sid}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage-only", action="store_true")
    a = ap.parse_args()
    stage()
    if not a.stage_only:
        publish()
