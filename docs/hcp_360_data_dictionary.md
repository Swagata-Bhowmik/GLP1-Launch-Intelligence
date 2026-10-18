# HCP 360 data dictionary

`data/03_processed/hcp_360.parquet`: **one row per prescriber (NPI)**, built by `src/glp1_intel/data_processing/hcp360.py` (notebook 03).

**Universe:** every Medicare Part D 2024 prescriber who wrote a GLP-1 **or** any other diabetes drug (316,559 doctors: 199,831 GLP-1 prescribers + 116,728 diabetes-only).
**Period:** prescribing = calendar 2024 (Medicare Part D only); payments = 2024–2025; registry = October 2026 snapshot; state context = Medicaid 2024–2025.

## Identity (Part D)
| Column | Meaning |
|---|---|
| `npi` | National Provider Identifier, the unique 10-digit doctor ID (text). **Primary key** |
| `last_name`, `first_name` | As reported by CMS (public). Hidden in notebooks; shown only where needed (rep view) |
| `city`, `state`, `state_fips` | Prescriber location in Part D. `state_fips` is text to keep leading zeros |
| `specialty` | Part D prescriber type (e.g. Endocrinology, Family Practice, Nurse Practitioner) |

## Registry (NPPES, Oct 2026)
| Column | Meaning |
|---|---|
| `credential` | Free text (MD, DO, NP, PA-C…); blank for ~8% |
| `sex` | NPPES sex code (F, M, X, U); blank for organisations / deactivated NPIs |
| `practice_zip5` | 5-digit practice-location ZIP: key for maps and territories |
| `taxonomy` | Primary NUCC taxonomy code (e.g. `207RE0101X` = Endocrinology) |
| `npi_year` | Year the NPI was issued (proxy for career stage; 2005 = the first year NPIs existed) |
| `npi_deactivated` | True if the NPI was deactivated after 2024 (retired, deceased, merged); exclude from call plans |

## Practice size (Part D, all drugs)
| Column | Meaning |
|---|---|
| `all_drug_claims` | All Part D claims written in 2024, any drug |
| `all_drug_cost` | Total gross cost of those claims (US$, before rebates) |
| `n_drugs` | Number of distinct drugs prescribed (each with ≥ 11 claims) |

## Other diabetes drugs (Part D, claims)
| Column | Meaning |
|---|---|
| `dm_non_glp1_claims` | All non-GLP-1 diabetes drug claims (sum of the classes below) |
| `dm_metformin_claims` | Metformin (incl. combinations not assigned to a newer class) |
| `dm_sglt2_claims` | SGLT2 inhibitors (empagliflozin, dapagliflozin…). ⚠️ also used for heart failure / CKD |
| `dm_dpp4_claims` | DPP-4 inhibitors (sitagliptin, linagliptin…) |
| `dm_insulin_claims` | Insulins (supplies such as syringes and pumps excluded) |
| `dm_su_claims` | Sulfonylureas (glipizide, glimepiride, glyburide) |
| `dm_tzd_claims` | Pioglitazone |
| `dm_other_oral_claims` | Acarbose, repaglinide, nateglinide, pramlintide |

## GLP-1 prescribing (Part D)
| Column | Meaning |
|---|---|
| `glp1_claims`, `glp1_cost` | All GLP-1 claims and gross cost |
| `glp1_benes_known` | Sum of patient counts **where not suppressed** (CMS hides counts < 11), so a lower bound |
| `glp1_rows_benes_suppressed` | Number of this doctor's GLP-1 rows with a suppressed patient count |
| `glp1_n_brands` | Distinct GLP-1 brands prescribed |
| `tirzepatide_claims`, `semaglutide_claims`, `dulaglutide_claims`, `liraglutide_claims`, `exenatide_claims` | Claims by molecule |
| `mounjaro_claims`, `zepbound_claims`, `ozempic_claims`, `wegovy_claims`, `rybelsus_claims`, `trulicity_claims` | Claims by brand |
| `glp1_ge65_claims_known` | GLP-1 claims for patients 65+ where not suppressed |

## Industry payments (Open Payments 2024–2025, Lilly and Novo Nordisk)
Present once the download has finished (`op_years` lists the years included). A value of 0 means **no payment reported**.
| Column | Meaning |
|---|---|
| `op_lilly_payments`, `op_novo_payments` | Number of payment records from each company (all products) |
| `op_lilly_usd`, `op_novo_usd` | Total US$ |
| `op_lilly_glp1_payments`, `op_novo_glp1_payments` | Payments whose first listed product is a GLP-1 brand |
| `op_lilly_meals`, `op_novo_meals` | Food-and-beverage payments (proxy for rep contact) |
| `op_lilly_speaker_consult_usd`, `op_novo_speaker_consult_usd` | Speaker, faculty and consulting fees (KOL signal) |

## State context (Medicaid SDUD)
| Column | Meaning |
|---|---|
| `state_medicaid_obesity_rx_2025` | Medicaid prescriptions of obesity GLP-1s (Zepbound, Wegovy, Saxenda) in the doctor's state, 2025 |
| `state_medicaid_obesity_growth_24_25` | 2025 ÷ 2024 of the same (2.0 = doubled) |

## Derived features
| Column | Formula | Use |
|---|---|---|
| `diabetes_total_claims` | `glp1_claims + dm_non_glp1_claims` | Size of the diabetes patient base: **potential** |
| `glp1_adopter` | `glp1_claims > 0` | Adopter vs non-adopter |
| `glp1_share_of_diabetes` | `glp1_claims / diabetes_total_claims` | How far GLP-1s are adopted: **current value** |
| `tirzepatide_share` | `tirzepatide / (tirzepatide + semaglutide)` | Molecule loyalty |
| `lilly_glp1_share` | `(tirzepatide + dulaglutide) / glp1_claims` | Company share for this doctor |
| `glp1_decile` | Deciles of `glp1_claims` among adopters (1 = top 10%) | GLP-1 volume tier |
| `diabetes_decile` | Deciles of `diabetes_total_claims` over the universe (1 = top 10%) | Potential tier |

## Known limitations
Medicare-only prescribing; CMS drops rows with < 11 claims (small prescribers under-counted); costs are gross, before rebates; state context is the same for all doctors in a state; payments are an engagement proxy, not a measure of influence.
