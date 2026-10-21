"""Quality gate for synthetic visit notes: pure Python, no project imports (Colab downloads this file as-is).

A generated note is accepted only if it faithfully expresses its scenario's labels:
    - every product discussed and every competitor named is mentioned
    - the side-effect term appears (via aliases) exactly when the scenario says it should
    - negated side effects carry a negation cue; reported ones do not
    - no leaked prompt words ("Attitude:", "about 80 words"), no headings, no doctor surnames
Interest level can't be checked by rules; the hand-labelled sample measures it (notebook 09).
"""
import re

NEGATION = r"\b(no|not|never|without|denies|denied|deny|none|didn't|did not|hasn't|haven't|wasn't|isn't|free of)\b"

# Everyday words reps use for each FAERS (MedDRA) term
AE_ALIASES = {
    "nausea": ["nausea", "nauseous", "nauseated", "queasy"],
    "vomiting": ["vomiting", "vomited", "vomit", "throwing up", "threw up"],
    "diarrhoea": ["diarrhoea", "diarrhea", "loose stools"],
    "constipation": ["constipation", "constipated"],
    "abdominal pain": ["abdominal pain", "stomach pain", "belly pain", "abd pain", "stomach ache"],
    "abdominal pain upper": ["abdominal pain", "stomach pain", "upper abdominal", "epigastric", "abd pain"],
    "abdominal discomfort": ["abdominal discomfort", "stomach discomfort", "GI discomfort"],
    "dyspepsia": ["dyspepsia", "indigestion", "heartburn"],
    "eructation": ["eructation", "burping", "belching"],
    "fatigue": ["fatigue", "tired", "tiredness", "exhausted"],
    "headache": ["headache", "headaches"],
    "dizziness": ["dizziness", "dizzy", "lightheaded"],
    "decreased appetite": ["decreased appetite", "reduced appetite", "loss of appetite", "no appetite", "appetite"],
    "weight decreased": ["weight loss", "lost weight", "losing weight", "weight decreased"],
    "weight increased": ["weight gain", "gained weight", "weight increased"],
    "blood glucose increased": ["blood glucose", "blood sugar", "glucose", "sugars"],
    "hypoglycaemia": ["hypoglycaemia", "hypoglycemia", "low blood sugar", "hypo"],
    "injection site pain": ["injection site pain", "injection site", "site pain", "pain at the injection"],
    "injection site erythema": ["injection site", "redness"],
    "pancreatitis": ["pancreatitis"],
    "thyroid tumours": ["thyroid"],
    "vision loss": ["vision", "eye"],
    "depression": ["depression", "depressed", "mood"],
    "gallbladder problems": ["gallbladder", "gallstones", "gallstone"],
    "malaise": ["malaise", "unwell", "feeling off"],
    "gastrooesophageal reflux disease": ["reflux", "GERD", "heartburn"],
    "flatulence": ["flatulence", "gas", "bloating"],
    "abdominal distension": ["bloating", "bloated", "distension"],
    "alopecia": ["alopecia", "hair loss", "hair thinning"],
}
FORBIDDEN = [
    r"\battitude\s*:", r"\binterest(?: level)?\s*:", r"\bobjections?\s*:", r"\bside effects?\s*:", r"\bcompetitors?\s*:",
    r"\bno competit", r"\babout \d+ words\b", r"\b\d+ words\b", r"\[name\]", r"\bscenario\b", r"^#", r"\*\*",
    r"\bDr\.\s+(?!(?:said|says|is|was|has|had|asked|agreed|mentioned|wants|likes|noted|thinks|felt|will|would|seemed|prefers|already|still|reports|reported|not|and|at|in|on)\b)[A-Z][a-z]{2,}",
]


def aliases(term: str) -> list[str]:
    """Words that count as a mention of a FAERS term (falls back to the term's longest word)."""
    term = (term or "").lower()
    if term in AE_ALIASES:
        return AE_ALIASES[term]
    words = [w for w in re.findall(r"[a-z]+", term) if len(w) >= 5]
    return [term] + ([max(words, key=len)] if words else [])


def find_mentions(note: str, words: list[str]) -> list[tuple[int, int]]:
    """Character spans of whole-word, case-insensitive matches."""
    spans = []
    for w in words:
        spans += [(m.start(), m.end()) for m in re.finditer(r"(?<![A-Za-z])" + re.escape(w) + r"(?![A-Za-z])", note, re.I)]
    return sorted(set(spans))


def check(note: str, scenario: dict) -> list[str]:
    """Return a list of problems; an empty list means the note passes."""
    problems = []
    if not note or len(note.split()) < 15:
        return ["too short"]
    stray = [ln for ln in note.splitlines()
             if ln.strip() and not ln.strip().startswith(("-", "•", "*")) and len(ln.split()) <= 2]
    if len(stray) >= 2:
        problems.append("junk lines")
    for brand in scenario["products_discussed"]:
        if not find_mentions(note, [brand]):
            problems.append(f"missing product {brand}")
    for brand in scenario["competitor_mentions"]:
        if not find_mentions(note, [brand]):
            problems.append(f"missing competitor {brand}")
    for pat in FORBIDDEN:
        # the doctor-surname rule needs case (capitalised name); every other rule ignores case
        flags = re.M if pat.startswith(r"\bDr") else re.I | re.M
        if re.search(pat, note, flags):
            problems.append(f"forbidden pattern {pat}")
    mode, term = scenario["ae_mode"], scenario.get("ae_term", "")
    if mode != "none":
        hits = find_mentions(note, aliases(term))
        if not hits:
            problems.append(f"missing side effect '{term}'")
        else:
            negated = any(re.search(NEGATION, note[max(0, s - 45):s], re.I) for s, _ in hits)
            if mode == "negated" and not negated:
                problems.append("side effect should be negated")
            if mode == "reported" and negated:
                problems.append("reported side effect looks negated")
    return problems
