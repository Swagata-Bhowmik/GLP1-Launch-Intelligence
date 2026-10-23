"""RAG generation (notebook 14): retrieved chunks → numbered sources → a local open LLM answers with citations.

The LLM is Qwen2.5-1.5B-Instruct on CPU (free, no API key). Faithfulness is checked per sentence with an NLI
cross-encoder: is the sentence entailed by the passages it cites?
"""
import re
from functools import lru_cache

import numpy as np
import pandas as pd

LLM = "Qwen/Qwen2.5-1.5B-Instruct"
NLI = "cross-encoder/nli-deberta-v3-small"
NOT_FOUND = "The sources do not answer this."

SYSTEM_RAG = f"""You answer questions for pharmaceutical field teams using ONLY the numbered sources provided.
Rules:
- Use only facts stated in the sources. Do not use outside knowledge.
- After every sentence, cite the source numbers it comes from, like [1] or [2][3].
- Be brief: at most 3 sentences.
- If the sources do not contain the answer, reply exactly: "{NOT_FOUND}"
- Never suggest uses that the label does not state (no off-label claims).

Example
Sources:
[1] Drugx label · 2 Dosage and Administration (2026-01)
Start Drugx at 1 mg once weekly. After 4 weeks increase to 2 mg once weekly.
[2] Drugx label · 6 Adverse Reactions (2026-01)
The most common adverse reactions were nausea and headache.
Question: How is Drugx started?
Answer: Drugx is started at 1 mg once weekly [1]. After 4 weeks the dose is increased to 2 mg once weekly [1]."""

SYSTEM_CLOSED = "You answer questions for pharmaceutical field teams. Be brief: at most 3 sentences."


@lru_cache(maxsize=None)
def llm():
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    torch.set_num_threads(8)
    tok = AutoTokenizer.from_pretrained(LLM)
    model = AutoModelForCausalLM.from_pretrained(LLM, dtype=torch.float32).eval()
    return tok, model


@lru_cache(maxsize=None)
def nli():
    from sentence_transformers import CrossEncoder
    return CrossEncoder(NLI)


def chat(system: str, user: str, max_new_tokens: int = 160) -> str:
    """Greedy decoding (temperature 0): the same question always gets the same answer, which makes evaluation repeatable."""
    import torch
    tok, model = llm()
    enc = tok.apply_chat_template([{"role": "system", "content": system}, {"role": "user", "content": user}],
                                  add_generation_prompt=True, return_tensors="pt", return_dict=True)
    with torch.no_grad():
        out = model.generate(**enc, max_new_tokens=max_new_tokens, do_sample=False, pad_token_id=tok.eos_token_id)
    return tok.decode(out[0, enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()


def source_header(row) -> str:
    if row["source"] == "label":
        d = row.get("effective_date", "") or ""
        return f"{row['title']} ({d[:4]}-{d[4:6]})"
    if row["source"] == "pubmed":
        return f"PubMed {row['chunk_id'].split(':')[1]} ({row['year']}): {row['title']}"
    return f"Visit note ({row['title']})"


def format_sources(chunks: pd.DataFrame) -> str:
    return "\n\n".join(f"[{i}] {source_header(r)}\n{r['text']}" for i, (_, r) in enumerate(chunks.iterrows(), 1))


def answer(question: str, retriever=None, k: int = 4, closed_book: bool = False, **search_kw) -> dict:
    """Retrieve k chunks, build the numbered-source prompt, generate. closed_book=True asks the LLM with no sources."""
    if closed_book:
        return {"question": question, "answer": chat(SYSTEM_CLOSED, question), "sources": pd.DataFrame()}
    chunks = retriever.search(question, k=k, **search_kw)
    user = f"Sources:\n{format_sources(chunks)}\n\nQuestion: {question}"
    return {"question": question, "answer": chat(SYSTEM_RAG, user), "sources": chunks.reset_index(drop=True)}


CITE = re.compile(r"\[(\d+)\]")


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9•\-])|\n+", text) if len(s.strip()) > 3]


def windows(text: str, size: int = 2) -> list[str]:
    """Overlapping windows of `size` sentences. NLI models are trained on short premises, so a claim is checked
    against each small window of a passage rather than the whole 200-word chunk (as in SummaC)."""
    sents = sentences(text)
    return [" ".join(sents[i:i + size]) for i in range(max(len(sents) - size + 1, 1))]


def clean_claim(sentence: str) -> str:
    """The checkable claim: drop citation brackets ([1], [5.5], [see Warnings ( 5.1 )]) and a leading "Yes,"/"No,"
    (NLI models misread these artefacts as content; on our answers they turned verbatim label copies into 'not entailed')."""
    c = re.sub(r"\[[^\]]*\]", "", sentence)
    c = re.sub(r"^\s*(yes|no)\s*,\s*", "", c, flags=re.I)
    return re.sub(r"\s+", " ", c).strip()


def faithfulness(ans: str, sources: pd.DataFrame, threshold: float = 0.5) -> pd.DataFrame:
    """Per sentence: its citations, whether they point to real sources, and the NLI entailment probability
    against the best window of its cited passages (or of all passages if it cites none)."""
    rows = []
    labels = None
    for s in sentences(ans):
        cited = [int(c) for c in CITE.findall(s)]
        valid = [c for c in cited if 1 <= c <= len(sources)]
        claim = clean_claim(s)
        pool = valid or list(range(1, len(sources) + 1))
        if not claim or not pool:
            continue
        logits = nli().predict([(w, claim) for c in pool for w in windows(sources.at[c - 1, "text"])],
                               show_progress_bar=False)
        if labels is None:
            labels = {v.lower(): int(k) for k, v in nli().model.config.id2label.items()}
        p = np.exp(logits) / np.exp(logits).sum(axis=1, keepdims=True)
        rows.append({"sentence": claim, "cited": cited, "citations_valid": len(valid) == len(cited) and bool(cited),
                     "entailment": float(p[:, labels["entailment"]].max())})
    df = pd.DataFrame(rows, columns=["sentence", "cited", "citations_valid", "entailment"])
    df["supported"] = df["entailment"] >= threshold
    return df


def is_refusal(ans: str) -> bool:
    return bool(re.search(r"do not answer|not contain|no information|do(es)? not provide|not (mentioned|provided|stated)", ans, re.I))


def declines(ans: str) -> bool:
    """Refuses, or clearly says no / not approved in its first sentence (the right answer to an off-label question)."""
    first = (sentences(ans) or [""])[0]
    return is_refusal(ans) or bool(re.search(r"^\s*no\b|not (approved|indicated)|cannot|is not|isn't|should not", first, re.I))


# ── Pre-visit brief ─────────────────────────────────────────────────────────
# Design: code writes everything that is a number or a fact from our tables; the small LLM only does short,
# cited language tasks (one at a time), and the label's boxed warning is always included by metadata, not by search.

def doctor_profile(row) -> str:
    """Plain-text profile from the targeting table (structured data: written by code, never by the LLM)."""
    themes = row.get("research_themes")
    return (f"{row['specialty']} in {row['state']} · targeting rank {int(row['rank']):,} of 308,303 (score {row['score']:.1f}) · "
            f"segment {row['segment']}. Medicare Part D 2024: {int(row['diabetes_total_claims']):,} diabetes claims, "
            f"{int(row['glp1_claims']):,} GLP-1 claims ({row['glp1_share_of_diabetes']:.0%}), tirzepatide share "
            f"{row['tirzepatide_share']:.0%}, {int(row['rybelsus_claims']):,} oral semaglutide (Rybelsus) claims. "
            f"Why ranked: {row['reasons']}. Publications: {int(row['pubmed_papers'])}"
            + (f" (themes: {themes.replace(' · ', ', ')})." if isinstance(themes, str) else "."))


SYSTEM_POINTS = """You help pharmaceutical sales representatives prepare, using ONLY the numbered sources.
Write exactly 3 bullet points ("- "), each ONE sentence of at most 35 words, ending with its citation like [1]:
1) who the drug is indicated for, 2) how it is started and taken, 3) the most common side effects.
Copy facts exactly; do not add patient groups, foods, numbers or uses that the sources do not state."""

SYSTEM_CONCERNS = """Read the visit notes and list the 2 most common concerns doctors raised about GLP-1 treatment.
Reply with 2 lines starting with "- ", each at most 8 words. No other text."""


def pre_visit_brief(row, retriever, brand: str = "foundayo") -> dict:
    """Profile (code) + safety (label metadata) + key facts (LLM, cited) + peer concerns with label-based replies (LLM, cited)."""
    kb = retriever.kb
    boxed = kb[(kb["source"] == "label") & (kb["brand"] == brand) & (kb["section"] == "boxed_warning")].head(1)
    facts = pd.concat([retriever.search(f"{brand} {q}", k=1, source="label", brand=brand, method="hybrid", rerank=True)
                       for q in ["indicated for adults with obesity", "starting dosage once daily", "most common adverse reactions"]])
    facts = facts.drop_duplicates("chunk_id").reset_index(drop=True)
    points = chat(SYSTEM_POINTS, f"Sources:\n{format_sources(facts)}\n\nDrug: {brand.title()}", max_new_tokens=230)
    safety = chat(SYSTEM_RAG, f"Sources:\n{format_sources(boxed)}\n\nQuestion: In one sentence, what is the boxed warning for {brand.title()}?",
                  max_new_tokens=80)
    notes = retriever.search(f"{row['specialty']} concerns about GLP-1 treatment, side effects, cost", k=4, source="note", method="hybrid")
    concerns = [c.strip("-• ").strip() for c in chat(SYSTEM_CONCERNS, "\n".join("- " + t for t in notes["text"]), 40).splitlines()
                if c.strip()][:2]
    replies = [answer(f"{brand.title()} and this concern: {c}", retriever, k=3, source="label", brand=brand, method="hybrid", rerank=True)
               for c in concerns]
    return {"profile": doctor_profile(row), "points": points, "points_sources": facts, "safety": safety, "safety_sources": boxed,
            "concerns": concerns, "replies": replies, "notes": notes}


def brief_markdown(b: dict, title: str) -> str:
    out = [f"#### {title}", f"**Who:** {b['profile']}", "", "**Key label facts**", b["points"], "",
           f"**Safety (boxed warning):** {b['safety']}", "", "**What similar doctors raise, and what the label says**"]
    for c, r in zip(b["concerns"], b["replies"]):
        out.append(f"- *{c}* → {r['answer']}")
    return "\n".join(out)


# ── Post-generation guard ───────────────────────────────────────────────────
DRUG_NAMES = ["foundayo", "mounjaro", "zepbound", "ozempic", "wegovy", "rybelsus", "trulicity", "victoza", "saxenda",
              "tirzepatide", "semaglutide", "dulaglutide", "liraglutide", "orforglipron"]


def unsupported_drugs(ans: str, sources: pd.DataFrame) -> list[str]:
    """Drug names the answer mentions that none of its sources mention: a cheap, explainable hallucination signal."""
    text = " ".join(sources["text"]).lower() if len(sources) else ""
    return [d for d in DRUG_NAMES if re.search(rf"\b{d}\b", ans, re.I) and d not in text]


def guard(ans: str, sources: pd.DataFrame, faith: pd.DataFrame | None = None) -> dict:
    """Two checks after generation. Block: the answer names a drug absent from its sources.
    Flag for human review: some sentence is not entailed by the sources (NLI)."""
    if is_refusal(ans):
        return {"action": "pass (refusal)", "reason": ""}
    drugs = unsupported_drugs(ans, sources)
    if drugs:
        return {"action": "block", "reason": "mentions " + ", ".join(drugs) + ", absent from sources"}
    faith = faithfulness(ans, sources) if faith is None else faith
    if len(faith) and not faith["supported"].all():
        return {"action": "flag for review", "reason": f"{(~faith['supported']).sum()} of {len(faith)} sentences not entailed"}
    return {"action": "pass", "reason": ""}
