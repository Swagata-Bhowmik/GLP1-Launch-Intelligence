# GLP-1 Rep Visit Notes (synthetic) v1

**1,055 synthetic sales-representative visit notes** about US GLP-1 medicines (2026 context), each with
classification labels (interest level, objections, side-effect mode, competitor mentions) and NER spans
(DRUG, ADVERSE_EVENT, DOSE) with BIO tags. **All notes are synthetic. No real doctors, patients or reps.**

- Generator: Qwen2.5-7B-Instruct (Apache 2.0), 4-bit, temperature 0.8, few-shot prompt; labels fixed before generation
- Grounding: specialties/states from CMS Part D 2024, side-effect terms sampled from openFDA FAERS frequencies
- Quality: rule-based gate with regeneration; 92% passed within 3 attempts; final 1,055 after the tightened gate
- Splits: train 738, validation 159, test 158
- Intended use: teaching and benchmarking NLP for pharma field notes (classification, NER, adverse-event flagging)
- Not for: clinical decisions, pharmacovigilance reporting, or any claim about real prescribers
- Limitations: one generator model, so its style and biases; interest level checked only on a human sample; doses rare
