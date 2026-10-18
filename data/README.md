# Data

Pipeline stages: **`01_raw` → `02_interim` → `03_processed`**, plus `04_synthetic_visit_notes`.
Raw files are never edited; every transformation happens in code (`notebooks/`, `src/glp1_intel/`).
Large files are git-ignored; see `PROJECT_HANDOFF.md` Section 6 for how to re-download.

| Folder | Source | Status |
|---|---|---|
| `01_raw/medicare_part_d_prescribers/` | CMS Medicare Part D Prescribers by Provider and Drug, 2024 (data.cms.gov) | ✅ `medicare_part_d_prescribers_by_provider_and_drug_2024.csv`: 4.43 GB, 28,023,892 rows, 22 cols |
| `01_raw/open_payments_industry_to_doctor/` | CMS Open Payments General Payments 2024–2025 (filter Lilly, Novo Nordisk) | ⏳ |
| `01_raw/nppes_doctor_registry/` | NPPES NPI Registry API (specialty, address) | ⏳ |
| `01_raw/medicaid_state_drug_utilization/` | Medicaid State Drug Utilization Data 2024–2026 | ⏳ |
| `01_raw/fda_faers_side_effect_reports/` | openFDA FAERS (tirzepatide, semaglutide, orforglipron, dulaglutide) | ⏳ |
| `01_raw/fda_drug_labels/` | openFDA / DailyMed labels (Mounjaro, Zepbound, Foundayo, Ozempic, Wegovy, Trulicity, Rybelsus) | ⏳ |
| `01_raw/pubmed_research_papers/` | PubMed abstracts + authors (GLP-1, obesity, orforglipron) | ⏳ |
| `01_raw/clinicaltrials_gov_studies/` | ClinicalTrials.gov API v2 (GLP-1 trials, investigators) | ⏳ |
| `01_raw/ade_corpus_training_data/` | Hugging Face `ade-benchmark-corpus/ade_corpus_v2` | ⏳ |
| `02_interim/` | `part_d_2024_glp1.parquet`: GLP-1 subset, 420,364 rows, 199,831 prescribers, 11.4 MB (made by notebook 02) | ✅ |
| `03_processed/` | e.g. `hcp_360.parquet` (one row per doctor), targeting scores | ⏳ |
| `04_synthetic_visit_notes/` | LLM-generated rep notes, grounded + partly hand-labelled (**synthetic**) | ⏳ |

## Part D 2024 columns
`Prscrbr_NPI` (doctor ID) · `Prscrbr_Last_Org_Name` · `Prscrbr_First_Name` · `Prscrbr_City` · `Prscrbr_State_Abrvtn` · `Prscrbr_State_FIPS` · `Prscrbr_Type` (specialty) · `Prscrbr_Type_Src` · `Brnd_Name` · `Gnrc_Name` · `Tot_Clms` (prescriptions incl. refills) · `Tot_30day_Fills` · `Tot_Day_Suply` · `Tot_Drug_Cst` (US$) · `Tot_Benes` (patients; blank if <11) · `GE65_*` (same metrics for patients 65+, with suppression flags)

GLP-1 generic names to filter: `Tirzepatide`, `Semaglutide`, `Dulaglutide`, `Liraglutide`, `Exenatide`, `Exenatide Microspheres` (Bydureon BCise), `Insulin Degludec/Liraglutide`. Excluded: `Teduglutide` (GLP-2), `Insulin Glargine/Lixisenatide` (Soliqua).
