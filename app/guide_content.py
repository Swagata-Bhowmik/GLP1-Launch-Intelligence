"""Project guide content: one source for the app's guide pages, the "How to read this page" boxes on every page,
and the standalone project report (deploy/build_report.py). Edit the text here, never in two places.

Every number is taken from the notebooks' outputs, reports/evaluation/*.json or app/data (see README "Results").
"""

APP = "https://glp1-launchlens.streamlit.app/"
REPO = "https://github.com/Swagata-Bhowmik/GLP1-Launch-Intelligence"
HF = "https://huggingface.co/SwagataBhowmik"
NBVIEWER = "https://nbviewer.org/github/Swagata-Bhowmik/GLP1-Launch-Intelligence/blob/main/notebooks/"
GITHUB_NB = REPO + "/blob/main/notebooks/"

# ── the project in a few lines ────────────────────────────────────────────────
SUMMARY = {
    "one_line": "LaunchLens is an open-source AI analytics platform for pharma sales-optimization teams, built on real "
                "public US data, for the 2026 GLP-1 market shift: which doctors to prioritise, why, and what to discuss.",
    "problem": "In 2026 the US GLP-1 market changed twice: Foundayo (orforglipron), the first GLP-1 weight-loss pill, was "
               "approved in April, and Medicare began paying for GLP-1 weight-loss treatment through the GLP-1 Bridge in July. "
               "Sales teams must re-decide which doctors to see and what to say. The evidence exists but is scattered: "
               "28 million prescription rows, payment records, research papers, FDA labels, side-effect reports and "
               "unstructured visit notes.",
    "solution": "One pipeline from raw public data to a live app: a profile for every doctor (HCP 360), a transparent "
                "targeting score, NLP models that read visit notes, a cited question-answering system (RAG) and a "
                "tool-using AI agent. Every model is measured against a simple baseline, and the failures are published.",
    "novelty": "The product idea is not new: Veeva, ZS and IQVIA sell similar tools inside companies. The contribution "
               "is doing it openly, on real public data, with honest evaluation, focused on 2026, plus an open "
               "synthetic visit-notes dataset (real field notes are never public).",
    "users": "Analysts (main users): market and targeting pages. Sales reps (secondary): pre-visit brief and visit log.",
}

# ── data sources ─────────────────────────────────────────────────────────────
DATA = [
    ("Medicare Part D Prescribers 2024", "CMS", "Prescriptions per doctor per drug",
     "28,023,892 rows (4.43 GB) → 420,364 GLP-1 rows, 199,831 prescribers", "Market, HCP 360, targeting"),
    ("NPPES NPI Registry", "CMS", "Every prescriber's specialty, address and status", "1.16 GB zip, streamed", "Specialty, location"),
    ("Open Payments 2024–2025", "CMS", "Industry payments to doctors", "~2.0M rows (two GLP-1 manufacturers)", "Industry-contact signal"),
    ("Medicaid State Drug Utilization", "CMS", "GLP-1 prescriptions per state per quarter, to Q1 2026", "26,202 rows", "Latest trend"),
    ("openFDA drug labels", "FDA", "Prescribing information for 9 GLP-1 brands", "9 labels → 798 chunks", "Label facts, RAG"),
    ("openFDA FAERS", "FDA", "Side-effect report counts, 6 molecules", "e.g. tirzepatide 160,551 reports", "Safety page, agent"),
    ("PubMed", "NIH", "Abstracts, authors, affiliations", "8,900 papers → 6,160 abstracts", "Topics, research signal, retrieval"),
    ("ClinicalTrials.gov", "NIH", "Studies for 7 GLP-1 molecules", "1,871 studies", "Research activity"),
    ("ADE Corpus v2", "Hugging Face", "Sentences labelled as describing a side effect or not", "20,896 sentences", "Adverse-event detector"),
    ("Synthetic visit notes v1", "This project", "Rep notes with objections, side-effect context, NER spans",
     "1,055 notes (738 / 159 / 158)", "Note classifiers, NER"),
]

# ── how to use the website: a 5-minute tour ───────────────────────────────────
TOUR = [
    ("Home", "", "The 2026 story, the headline numbers and links to every page. Use the top menu or the “All pages” list."),
    ("Start here", "guide", "This page: what the project is, how to read the site, where to find what, and a glossary."),
    ("Market", "market", "Where is the opportunity? Brand sizes, a state map, and the Medicaid trend to Q1 2026."),
    ("Find doctors", "targeting", "Who to visit first? All 308,303 doctors ranked by a transparent score, with filters."),
    ("Doctor 360", "doctor", "Why this doctor? Type a last name (try “Jeet”) to see one profile and its score breakdown."),
    ("Pre-visit brief", "rep_brief", "What should the rep say? The doctor's numbers, verbatim FDA-label facts, likely objections."),
    ("Log a visit", "rep_note", "What happens after? Four NLP models read a visit note and flag possible side effects."),
    ("Safety", "safety", "What side effects are reported to the FDA? Context for doctors' questions, not drug comparison."),
    ("Ask AI", "ask_ai", "Can I just ask? 21 graded example questions answered by the AI agent, with every step shown."),
    ("Key numbers", "home", "The one-screen summary: four numbers and three findings."),
    ("Notebooks", "notebooks", "The 16 notebooks behind the site: what each did, its key result and the decision it led to."),
    ("Decisions & results", "decisions", "Every major design decision and why, targets vs results, limitations."),
]

# ── question → where to look ─────────────────────────────────────────────────
WHERE = [
    ("How big is the GLP-1 market? Which brands lead?", "Market (brand chart)", "04"),
    ("Where does tirzepatide do well or badly?", "Market (state map)", "04"),
    ("What happens when insurance stops paying?", "Market (Medicaid trend and state change)", "04"),
    ("Which doctors should a team visit first?", "Find doctors", "05"),
    ("Why is a specific doctor ranked high?", "Doctor 360", "05"),
    ("What should a rep know before a visit?", "Pre-visit brief", "13, 14"),
    ("Can AI read a visit note and spot side effects?", "Log a visit", "07, 11, 12"),
    ("What side effects get reported for each drug?", "Safety", "01, 04"),
    ("Can I ask questions in plain English?", "Ask AI", "15"),
    ("How was the data collected and cleaned?", "Notebooks 01–03", "01, 02, 03"),
    ("How good are the models, honestly?", "Decisions & results, Home → Proof", "17"),
    ("What was tried and did not work?", "Decisions & results → Limitations", "17"),
]

# ── words a reader may not know ──────────────────────────────────────────────
GLOSSARY = [
    ("GLP-1", "A drug class that copies a gut hormone, lowering blood sugar and appetite. Treats type 2 diabetes and obesity."),
    ("Semaglutide / tirzepatide", "The two leading molecules. Semaglutide (Novo Nordisk): Ozempic, Rybelsus, Wegovy. "
                                  "Tirzepatide (Eli Lilly): Mounjaro, Zepbound."),
    ("Foundayo (orforglipron)", "A GLP-1 weight-loss pill approved in April 2026."),
    ("Medicare Part D", "US government drug insurance for people aged 65+. CMS publishes prescriptions per doctor per drug yearly; 2024 is the latest."),
    ("Medicaid", "US government insurance for low-income people. State-level data runs to Q1 2026."),
    ("GLP-1 Bridge", "Medicare's 2026 programme paying for GLP-1 weight-loss treatment, from July 2026."),
    ("Claim", "One filled prescription (including refills) in Medicare data."),
    ("HCP / NPI", "Health-care professional (any prescriber) / the 10-digit ID every US prescriber has. All tables join on NPI."),
    ("HCP 360", "Our one-row-per-doctor table: 316,559 doctors × 61 columns from five public sources."),
    ("Tirzepatide share", "Tirzepatide claims ÷ (tirzepatide + semaglutide claims). US average 30.1% in 2024."),
    ("Open Payments", "Public CMS records of industry payments to doctors. We use it as a company-neutral “industry contact” signal."),
    ("FAERS", "The FDA's voluntary adverse-event (side-effect) reporting system. Counts show reporting, not rates."),
    ("Adverse event (ADE)", "A harmful effect after taking a drug. Companies must collect and report them."),
    ("F1 score", "0 to 1. Balances catching real cases (recall) and avoiding false alarms (precision). Higher is better."),
    ("Recall@5", "How often the right document appears in the top 5 search results."),
    ("TF-IDF", "A classic text method that counts informative words. Our baseline for every text task."),
    ("BERT / BiomedBERT", "Transformer language models. BiomedBERT was pre-trained on medical papers. We fine-tuned both."),
    ("NER", "Named-entity recognition: tagging words as drug, side effect or dose."),
    ("RAG", "Retrieval-augmented generation: the AI first searches documents, then answers only from them, with citations."),
    ("Agent", "An AI that chooses which tool (program) to run, with which inputs, to answer a question."),
    ("95% interval", "The range the score would likely fall in on a new test set of the same size."),
]

# ── the notebooks ────────────────────────────────────────────────────────────
NOTEBOOKS = [
    dict(n="01", file="01_data_collection_public_apis.ipynb", title="Data collection from public APIs", stage="Data",
         why="Gather every public source the project needs, reproducibly.",
         did="Reusable, resumable downloaders for openFDA labels and FAERS, PubMed, ClinicalTrials.gov, Medicaid, "
             "Open Payments, the NPPES registry and the ADE Corpus. The 4.4 GB Medicare file is downloaded manually.",
         result="9 public sources in data/01_raw (never edited). E.g. 8,900 PubMed papers, 1,871 trials, 9 FDA labels.",
         decision="Raw data stays untouched; every change happens in code (raw → interim → processed).",
         figure=None, page="Feeds every page"),
    dict(n="02", file="02_part_d_glp1_filter_and_profile.ipynb", title="Medicare Part D: GLP-1 filter and profile", stage="Data",
         why="The Medicare file has 28 million rows, too big for pandas or Excel.",
         did="DuckDB SQL streams the 4.43 GB CSV from disk and keeps 7 GLP-1 generic names.",
         result="420,364 GLP-1 rows and 199,831 prescribers in about 1 minute; 19,620,006 GLP-1 claims.",
         decision="DuckDB instead of pandas: query big files without loading them into memory.",
         figure=None, page="Home, Market"),
    dict(n="03", file="03_build_hcp_360_doctor_table.ipynb", title="HCP 360: one row per doctor", stage="Data",
         why="Prescribing, specialty, payments and research sit in different files.",
         did="Joins five sources on the NPI; drops deactivated NPIs; code assertions check that totals reconcile.",
         result="hcp_360.parquet: 316,559 doctors × 61 columns; 99.6% of NPIs matched the registry.",
         decision="One table as the single source of truth for the app, the score and the agent.",
         figure=None, page="Find doctors, Doctor 360"),
    dict(n="04", file="04_glp1_market_landscape_eda.ipynb", title="GLP-1 market landscape", stage="Data",
         why="Understand the market before modelling it.",
         did="Seven charts: brands, states, specialties, the Medicaid trend, coverage cuts, FAERS and research momentum.",
         result="Ozempic 9.9M vs Mounjaro 4.7M claims; tirzepatide share 18% (Oregon) to 45% (Utah); Medicaid obesity "
                "GLP-1s grew 27× then fell 40–50% in one quarter when four states ended coverage (Jan 2026).",
         decision="“Coverage decides volume” became the core story: the July 2026 Medicare Bridge is the same lever, reversed.",
         figure="04_4_medicaid_trend.png", page="Market, Key numbers"),
    dict(n="05", file="05_doctor_segmentation_and_targeting.ipynb", title="Doctor segmentation and targeting", stage="Data",
         why="Rank doctors for the 2026 opportunity, in a way a manager can explain.",
         did="A 0–100 weighted score from 7 components, 3 plain-English reasons per doctor, 6 segments, "
             "a ±20% weight-jitter robustness test, and k-means as a cross-check.",
         result="308,303 doctors scored. 96.5% of the top 10,000 stay in the top 10,000 under random weight changes "
                "(Spearman 0.999). k-means (silhouette 0.50) found a 35k-doctor oral-semaglutide group.",
         decision="A transparent weighted score, not a black-box model: there is no ground-truth label for “good target”, "
                  "and reps must see why.",
         figure="05_1_segments.png", page="Find doctors, Doctor 360"),
    dict(n="06", file="06_nlp_foundations_text_preprocessing.ipynb", title="NLP foundations: text preprocessing", stage="NLP basics",
         why="Turn research abstracts and labels into clean text for classical NLP.",
         did="Tokenisation, lemmatisation (spaCy), regex for doses and numbers, stop words (keeping negations), Zipf's law.",
         result="A reusable clean() function and the cleaned research/label corpus (6,160 abstracts after de-duplication).",
         decision="Keep negations (“no nausea” ≠ “nausea”), and keep raw text for transformers, which need it.",
         figure="06_3_zipf.png", page="Groundwork for notebooks 07–08"),
    dict(n="07", file="07_classical_nlp_tfidf_baselines.ipynb", title="Classical NLP: TF-IDF baselines", stage="NLP basics",
         why="Set an honest baseline that every later model must beat.",
         did="TF-IDF + logistic regression for adverse-event sentence detection; stratified splits, cross-validation, "
             "a recall-first threshold, and a leakage check.",
         result="Baseline F1 0.687. Duplicates had inflated cross-validated F1 to 0.84; after de-duplication it was 0.72.",
         decision="Always remove near-duplicates before splitting, and evaluate on the test set only once.",
         figure="07_2_pr_roc.png", page="Home → Proof (0.69 baseline)"),
    dict(n="08", file="08_word_embeddings_and_topic_modeling.ipynb", title="Word embeddings and topic modelling", stage="NLP basics",
         why="Find research themes and link doctors to them.",
         did="Word2Vec and fastText trained on PubMed; LDA vs BERTopic; emerging-topic trends.",
         result="Domain word vectors, research topics, and research-theme profiles for 736 doctors.",
         decision="Word vectors have one meaning per word, so later steps use contextual transformers.",
         figure="08_2_topic_map.png", page="Research signal in the score"),
    dict(n="09", file="09_synthetic_visit_notes_generation_and_labeling.ipynb", title="Synthetic visit notes", stage="Data for NLP",
         why="Real sales-rep visit notes are confidential, but the rep tools need them.",
         did="1,200 scenarios fixed the labels first; Qwen2.5-7B (open, free Colab GPU) wrote the notes; a rule-based "
             "quality gate rejected bad notes; NER tags came from lexicon matching.",
         result="An open dataset of 1,055 labelled notes (738 train / 159 validation / 158 test) with a dataset card.",
         decision="Labels before text, so labels are correct by construction. Weakness stated openly: models trained "
                  "on synthetic notes will look better than on real notes.",
         figure="09_1_dataset_labels.png", page="Log a visit, Pre-visit brief"),
    dict(n="10", file="10_transformers_explained_attention_to_bert.ipynb", title="Transformers explained", stage="Transformers",
         why="Understand the models before fine-tuning them.",
         did="Self-attention written in NumPy and checked against PyTorch; positional encoding; encoder vs decoder; "
             "fill-mask and attention heads in real BERT.",
         result="Concept demos and a comparison of the models used (BERT/BiomedBERT ~110M parameters, Qwen2.5 1.5B and 7B).",
         decision="Encoders (BERT) for classification and tagging; decoders (Qwen) for writing answers.",
         figure="10_2_attention_head.png", page="Theory behind notebooks 11–15"),
    dict(n="11", file="11_finetune_visit_note_classifier_huggingface.ipynb", title="Fine-tuning visit-note classifiers", stage="Transformers",
         why="Classify each note's objections and side-effect context.",
         did="Fine-tuned BERT and BiomedBERT with the Hugging Face Trainer (lr 3e-5, 4 epochs, batch 16) and compared "
             "them with TF-IDF using bootstrap 95% intervals.",
         result="Side-effect context: BERT macro-F1 0.97 (TF-IDF 0.86). Objections: TF-IDF 0.94 beat BiomedBERT 0.91.",
         decision="Pick the model per task by test results: transformers where context matters (negation), "
                  "TF-IDF where keywords suffice. The app uses both.",
         figure="11_1_model_comparison.png", page="Log a visit"),
    dict(n="12", file="12_ner_and_adverse_event_detection.ipynb", title="NER and adverse-event detection", stage="Transformers",
         why="Highlight drugs, side effects and doses, and flag possible adverse events for safety review.",
         did="BiomedBERT token classification (BIO tags) on visit notes; BiomedBERT sentence classifier on the ADE Corpus "
             "(20,896 sentences), with the threshold set for at least 90% recall.",
         result="NER entity F1 0.98 (drug 1.00, side effect 0.95). Adverse-event F1 0.90 vs 0.69 baseline; at 92% recall "
                "73 false alarms instead of 673.",
         decision="Tune for recall: missing a real adverse event is worse than a false alarm.",
         figure="12_1_ade_pr_comparison.png", page="Log a visit, Home → Proof"),
    dict(n="13", file="13_sentence_embeddings_and_vector_search.ipynb", title="Sentence embeddings and vector search", stage="Retrieval",
         why="The AI must find the right label passage or paper before answering.",
         did="Chunked labels, papers and notes (200 words, 40 overlap) into 8,013 chunks; compared BM25, MiniLM, BGE "
             "and a hybrid with rank fusion, a cross-encoder re-ranker and a brand filter; FAISS index.",
         result="Hybrid recall@5: 0.97 on label questions (BM25 0.73) and 0.87 on papers.",
         decision="Hybrid search: keywords catch exact drug names, embeddings catch meaning, and each fails differently.",
         figure="13_1_recall_at_k_pubmed.png", page="Pre-visit brief, Ask AI"),
    dict(n="14", file="14_rag_pre_visit_brief.ipynb", title="RAG: cited answers and the pre-visit brief", stage="Generation",
         why="Answer label questions without inventing facts.",
         did="Qwen2.5-1.5B on CPU answers only from retrieved passages, with citations; an NLI model checks each sentence; "
             "a guard blocks or flags unsupported answers.",
         result="21/30 correct with retrieval vs 4/30 for the same model alone; 77% of sentences supported (29% without).",
         decision="Code writes the facts and always adds the boxed warning; the LLM only does small cited steps.",
         figure="14_1_rag_vs_closed_book.png", page="Pre-visit brief, Home → Proof"),
    dict(n="15", file="15_llm_agent_ask_ai.ipynb", title="LLM agent: Ask AI", stage="Agents",
         why="Let a user ask questions in plain English across all the data.",
         did="An agent with 5 tools (doctor ranking, market summary, side-effect reports, label answers, note search); "
             "code computes every number; up to 3 tool calls.",
         result="12/21 answers fully correct; right tool 81%, right tool and filters 71%; 127 of 128 numbers traceable to a tool.",
         decision="After a real failure (a hazard ratio of 0.80 read as “80% reduction”), code-enforced provenance "
                  "(finalize) now carries tool warnings to the user.",
         figure="15_1_agent_vs_router.png", page="Ask AI"),
    dict(n="16", file=None, title="LoRA fine-tuning (planned)", stage="Fine-tuning",
         why="Adapt a small LLM cheaply to the domain.",
         did="Planned for a free Colab GPU; not run yet.",
         result="Not done.", decision="Listed as future work rather than claimed.", figure=None, page="—"),
    dict(n="17", file="17_evaluation_guardrails_report.ipynb", title="Evaluation, guardrails and fairness", stage="Evaluation",
         why="One honest scorecard for the whole project.",
         did="95% intervals for every result, an LLM-as-judge check against human grades, 10 guardrail tests including "
             "prompt injection, and a fairness audit of the targeting list.",
         result="LLM judge agrees with humans only 52% (κ 0.28). Guardrails 7/10; 1 of 3 prompt injections worked. "
                "Nurse practitioners are under-represented in the top list (0.69×).",
         decision="Publish the failures with the successes; humans grade, not a small LLM.",
         figure="17_1_scorecard_intervals.png", page="Home → Proof"),
]

# ── design decisions ─────────────────────────────────────────────────────────
DECISIONS = [
    ("Use real public US data", "Synthetic market data; Kaggle datasets",
     "Results reflect the real 2024 Medicare market. Limitation: Medicare covers people 65+, and 2024 is the latest doctor-level year.", "01–04"),
    ("DuckDB for the 28M-row file", "pandas, Spark",
     "Runs SQL on a 4.4 GB file from disk on a laptop in about a minute; pandas would run out of memory, Spark is overkill.", "02"),
    ("One table per doctor joined on NPI (HCP 360)", "Separate tables per page",
     "One source of truth: the score, the app and the agent all read the same numbers.", "03"),
    ("Transparent weighted score, not a machine-learning ranker", "Supervised model; pure clustering",
     "No ground-truth “good target” label exists, and managers must explain a ranking. Robustness was tested (96.5% stable); "
     "k-means was used only as a cross-check.", "05"),
    ("Company-neutral “industry contact” signal", "Payments from one company only",
     "Counts payments from either GLP-1 manufacturer; the project takes no company's side.", "03, 05"),
    ("Synthetic visit notes with labels fixed first", "Scraping notes; hand-writing notes",
     "Real notes are confidential. Fixing labels before generating text makes them correct by construction; a quality gate removes bad notes.", "09"),
    ("Baselines first, then transformers", "Going straight to BERT",
     "A model only matters if it beats a simple baseline. TF-IDF stayed in use where it won (objections).", "07, 11"),
    ("Remove duplicates before splitting", "Random split",
     "Duplicates inflated F1 from 0.72 to 0.84 (leakage); the honest number is reported.", "07"),
    ("Adverse-event threshold for ≥90% recall", "Default 0.5 threshold",
     "Missing a side effect is worse than a false alarm; BiomedBERT keeps false alarms low (73 vs 673).", "12"),
    ("Hybrid BM25 + BGE retrieval with a brand filter", "Keyword-only or embedding-only search",
     "Each method fails on different questions; together recall@5 reaches 0.97; the filter guarantees the right drug's label.", "13"),
    ("Small open LLM on CPU (Qwen2.5-1.5B)", "Paid API (GPT, Claude)",
     "Free, private and reproducible; no data leaves the machine. Cost: weaker reasoning, measured openly.", "14, 15"),
    ("Code writes facts; the LLM only phrases", "Let the LLM write the whole brief",
     "Numbers come from code; the boxed warning is added by metadata so it can never be dropped; an NLI guard checks sentences.", "14"),
    ("Agent numbers must come from tools (finalize)", "Trust the LLM's text",
     "A real failure (HR 0.80 read as “80% reduction”) showed the LLM can distort tool output; code now attaches provenance.", "15"),
    ("Humans grade the LLM tests", "LLM-as-judge only",
     "The small judge agreed with humans only 52% (κ 0.28) and was too lenient.", "17"),
    ("Free hosting: Streamlit Cloud + Hugging Face", "Paid server; Hugging Face Docker Space (needs PRO)",
     "Free and public. The live LLM features need ~6 GB of memory, so they are switched off online; the 21 evaluated agent runs are shown instead.", "App"),
]

# ── targets vs results ───────────────────────────────────────────────────────
RESULTS = [
    ("Adverse-event detection beats the TF-IDF baseline", "F1 0.90 [0.89–0.92] vs 0.69", "Met"),
    ("Catch ≥90% of adverse events with few false alarms", "92% recall with 73 false alarms (TF-IDF: 673)", "Met"),
    ("Tag drugs, side effects and doses in notes", "Entity F1 0.98 (dose 0.62, only 5 test cases)", "Met (dose weak)"),
    ("Classify note objections and side-effect context", "Macro-F1 0.94 (TF-IDF) and 0.97 (BERT)", "Met"),
    ("Find the right label passage", "Recall@5 0.97 (keywords only: 0.73)", "Met"),
    ("Retrieval improves LLM answers", "21/30 correct vs 4/30 without retrieval", "Met"),
    ("Agent answers questions correctly", "12/21 fully correct; right tool 81%", "Partly"),
    ("Guardrails stop unsafe answers", "7/10 tests; 1 of 3 prompt injections worked", "Partly"),
    ("A small LLM can replace human grading", "52% agreement, κ 0.28", "Not met"),
    ("Targeting is fair across specialties", "Nurse practitioners 0.69×, endocrinologists 1.57×", "Gap found"),
    ("LoRA fine-tuning (notebook 16)", "Planned, not run", "Not done"),
    ("Human check of 100 synthetic notes", "Prepared, not done", "Not done"),
]

LIMITATIONS = [
    "Visit notes are synthetic, so note models will score lower on real notes.",
    "Hand-graded LLM tests are small (21–30 questions), so their intervals are wide (about ±0.15).",
    "The 1.5B LLM follows instructions loosely and can invent answers to leading questions.",
    "Prompt injection worked once in 3 tries: a planted document could make the system claim off-label use.",
    "Medicare covers people 65+ and the latest doctor-level data is 2024; the 2026 opportunity is modelled.",
    "The score ranks individuals and under-weights team-based prescribers such as nurse practitioners.",
    "Guardrails are demonstrations, not a validated compliance or safety system.",
]

# ── "How to read this page" boxes, one per app page ───────────────────────────
PAGE_HELP = {
    "market": dict(
        question="Where is the GLP-1 opportunity, and what drives it?",
        read=["**Claims by brand:** one bar per brand, Medicare 2024. Colour = molecule. Ozempic (9.93M) is about twice Mounjaro (4.69M). "
              "Wegovy is tiny because Medicare did not pay for weight loss in 2024; the July 2026 Bridge changes that.",
              "**State map:** tirzepatide share of tirzepatide + semaglutide claims. Violet = above the 30% US average, teal = below. "
              "Hover a state for its numbers. Range: Rhode Island 15% to Utah 45%.",
              "**Medicaid trend (to Q1 2026):** prescriptions per quarter in thousands. Dashed lines are the weight-loss brands. "
              "The orange band marks January 2026, when four states ended obesity coverage.",
              "**Zepbound + Wegovy change by state:** orange bars are those four states (PA −96%, NH −88%, CA −76%, SC −62%); "
              "nationally about −45%.",
              "**Claims by specialty:** each label reads “claims · tirzepatide share · % of these doctors who prescribe GLP-1”."],
        meaning="Insurance coverage decides volume. The Medicare Bridge flips the same switch on for patients aged 65+.",
        source="Notebook 04 · Medicare Part D 2024, Medicaid State Drug Utilization to Q1 2026"),
    "targeting": dict(
        question="Which doctors should a team prioritise for the 2026 opportunity?",
        read=["**Score (0–100):** potential 30% · GLP-1 experience 20% · headroom 15% · tirzepatide openness 15% · "
              "oral affinity 10% · research 5% · coverage gap 5%. Each part is scaled 0–1 before weighting.",
              "**Filters:** state, specialty, segment, and “No industry contact” (no payment from either GLP-1 maker in 2024–25).",
              "**Four numbers:** doctors in view, their diabetes claims, the median score, and the % with no industry contact. They update with the filters.",
              "**Table:** rank, score and three plain-English reasons per doctor. “Download this list” exports it as CSV.",
              "**Segments:** A champions · B high-value swing (highest average score, 74) · C competitor strongholds · "
              "D untapped · E developing · F low volume."],
        meaning="A team can narrow 308,303 doctors to a short, explainable list. The score decides who receives "
                "label-consistent information first, never what a doctor should prescribe.",
        source="Notebook 05 · HCP 360 (notebook 03)"),
    "doctor": dict(
        question="Why is this doctor ranked where they are?",
        read=["Type a **last name** (try “Jeet” or “Anwar”) or a 10-digit **NPI**.",
              "**Header:** specialty, place, segment, score and rank out of 308,303.",
              "**Four numbers:** diabetes claims 2024, GLP-1 claims, GLP-1 as a % of diabetes prescriptions, industry payments from both GLP-1 makers.",
              "**Why this score:** points each of the 7 components contributes; the bars add up to the score.",
              "**Evidence:** plain-English reasons, plus linked papers or trials (matched by name, so verify)."],
        meaning="Nothing is hidden: every point of the score can be traced.",
        source="Notebooks 03 and 05"),
    "safety": dict(
        question="What side effects are reported to the FDA for each GLP-1?",
        read=["Pick molecules with the buttons. **Top chart:** reports received per quarter. **Bars:** the 10 most-reported reactions per molecule.",
              "Tirzepatide's top report is “incorrect dose administered” (29,672): pen and dosing questions, not a new medical signal.",
              "Foundayo (orforglipron) has 728 reports, almost all in 2026, because it is new."],
        meaning="FAERS counts show reporting, not how often side effects happen (voluntary, unverified, no denominator). "
                "Use it to anticipate doctors' questions, never to compare drug safety.",
        source="openFDA FAERS, collected in notebook 01"),
    "home": dict(
        question="What are the headline numbers and findings?",
        read=["**199,831** GLP-1 prescribers · **19.6M** GLP-1 claims (US$24.6bn gross spend) · **30.1%** tirzepatide share · "
              "**23%** of the 10,000 most Bridge-ready doctors had no payment from either GLP-1 maker.",
              "**Three findings:** coverage decides volume; share swings 2.5× by state; high-value doctors are under-reached."],
        meaning="Prescribing is Medicare 2024; trends to Q1 2026 are Medicaid; the 2026 opportunity is modelled, not observed.",
        source="Notebooks 02–05"),
    "rep_brief": dict(
        question="What should a sales rep know before visiting this doctor?",
        read=["Pick a **state**, optionally a specialty and the **product**, then one of the **top 20 doctors**. Default: Ohio, rank 35.",
              "**Four numbers:** rank and score, diabetes claims, GLP-1 claims (and their % of diabetes prescriptions), tirzepatide share.",
              "**What the label says:** sentences quoted verbatim from the FDA label with section and date. The boxed warning is always shown.",
              "**What similar doctors raise:** the share of synthetic visit notes (same specialty) mentioning each objection.",
              "**Draft with AI:** the RAG pipeline; switched off online because the LLM needs ~6 GB of memory."],
        meaning="Numbers come from code and label facts from the label itself, so the brief cannot invent claims.",
        source="Notebooks 05, 09, 13, 14"),
    "rep_note": dict(
        question="Can AI read a visit note and catch what matters?",
        read=["Edit the sample note or type your own; results update instantly.",
              "**Adverse-event check:** probability that the note describes a side effect; above the threshold it says “route to safety review”. Tuned for ≥90% recall.",
              "**Highlighted note:** violet = drug, coral = side effect, amber = dose (BiomedBERT NER). Hover a tag for its confidence.",
              "**Side-effect context:** none / concern / reported / negated, with confidence (BERT).",
              "**Objections raised:** e.g. cost, needles, efficacy (TF-IDF + logistic regression)."],
        meaning="Reps' notes are rarely read at scale; this flags safety-relevant notes and doctor concerns automatically.",
        source="Notebooks 07, 11, 12 · trained on ADE Corpus v2 and synthetic notes"),
    "ask_ai": dict(
        question="Can a manager ask questions in plain English?",
        read=["**Example questions (instant):** 21 questions run once and graded by hand: 12 correct, 5 partial, 4 wrong. "
              "Pick one to see the answer, its grade, and each tool the agent called with the data it got back.",
              "**Ask your own (live):** runs the real agent; switched off online (needs ~6 GB of memory; 1–3 minutes per question on a laptop)."],
        meaning="The LLM chooses the tool; code computes every number, and doctor names are never shown.",
        source="Notebook 15 · evaluated in notebook 17"),
}
