# Notebooks: learning ladder (basics → advanced)

Read in order. Each notebook explains the theory in plain language, then applies it to the project.

**Colour key** (same in every notebook; boxes come from `src/glp1_intel/notebook_style.py`):
🟣 section heading · 💡 concept / theory (orange) · 🛠️ what the next code does (mint) · 📊 reading the output (blue) · ⚠️ watch out (rose) · 🎯 key takeaways + interview questions (green).
Colours show in Jupyter, VS Code and Colab; GitHub's viewer keeps the icons and text but drops the colours.

| # | Notebook | Topic | Status |
|---|---|---|---|
| 01 | `01_data_collection_public_apis.ipynb` | Fetching public pharma data via APIs | ✅ (Open Payments section fills in when the download finishes) |
| 02 | `02_part_d_glp1_filter_and_profile.ipynb` | DuckDB on a 28M-row file; GLP-1 subset; first EDA | ✅ |
| 03 | `03_build_hcp_360_doctor_table.ipynb` | One row per doctor (data unification) | ✅ (payments section fills in later) |
| 04 | `04_glp1_market_landscape_eda.ipynb` | Market share, specialties, states, story | ✅ |
| 05 | `05_doctor_segmentation_and_targeting.ipynb` | Deciling, segmentation, targeting score | ✅ |
| 06 | `06_nlp_foundations_text_preprocessing.ipynb` | Tokenisation, stemming/lemmatisation, regex, spaCy | ✅ |
| 07 | `07_classical_nlp_tfidf_baselines.ipynb` | BoW, TF-IDF, Logistic Regression, metrics | ✅ |
| 08 | `08_word_embeddings_and_topic_modeling.ipynb` | Word2Vec, LDA, BERTopic | ✅ |
| 09 | `09_synthetic_visit_notes_generation_and_labeling.ipynb` | LLM synthetic data, labelling | ✅ (Colab generator: `colab/09a_…`) |
| 10 | `10_transformers_explained_attention_to_bert.ipynb` | Attention, transformers, BERT | ✅ |
| 11 | `11_finetune_visit_note_classifier_huggingface.ipynb` | HF Trainer fine-tuning | ⏳ |
| 12 | `12_ner_and_adverse_event_detection.ipynb` | Token classification, BIO, ADE detection | ⏳ |
| 13 | `13_sentence_embeddings_and_vector_search.ipynb` | Embeddings, FAISS, hybrid search | ⏳ |
| 14 | `14_rag_pre_visit_brief.ipynb` | RAG with citations | ⏳ |
| 15 | `15_llm_agent_ask_ai.ipynb` | Tool-using agent | ⏳ |
| 16 | `16_lora_finetuning_small_llm.ipynb` | LoRA/QLoRA (Colab) | ⏳ stretch |
| 17 | `17_evaluation_guardrails_report.ipynb` | Evaluation, hallucination, guardrails | ⏳ |
