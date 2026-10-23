import pandas as pd
import streamlit as st

import aurora as A

A.setup("Log a visit")
st.markdown("## Log a visit note")
st.caption("Paste or type a visit note. Four models from notebooks 11–12 read it instantly: drugs, doses and side effects are "
           "highlighted, possible adverse events are flagged for safety review, and doctor objections are tagged.")

SAMPLE = ("Saw Dr. at endo clinic, discussed Foundayo vs Ozempic 1 mg. One pt had severe vomiting after starting Ozempic, "
          "stopped it. Doc worried about cost and prior auth for Medicare pts, open to oral option for needle-averse pts.")
OBJ_TEXT = {"cost_coverage": "Cost / coverage", "gi_tolerability": "GI tolerability", "elderly_frailty": "Elderly / frailty",
            "efficacy_vs_comp": "Efficacy vs competitor", "injection_aversion": "Injection aversion",
            "supply_access": "Supply / access", "safety_other": "Other safety"}
AE_TEXT = {"none": "No side effect discussed", "concern": "Doctor raised a side-effect concern",
           "reported": "A patient side effect was reported", "negated": "Side effects explicitly denied"}

note = st.text_area("Visit note", SAMPLE, height=130)


@st.cache_resource
def analyzer():
    from glp1_intel.models import note_analyzer as N
    return N


N = analyzer()
missing = [k for k, ok in N.available().items() if not ok]
if missing:
    A.callout(f"Some trained models are not on this machine ({', '.join(missing)}). They are git-ignored; run notebooks 11–12 "
              "to create them. The rest of the analysis still runs.", "warn")

if note.strip():
    with st.spinner("Reading the note…"):
        r = N.analyze(note.strip())

    if r["pv_flag"]:
        flagged = [s for s in r["ade_sentences"] if s["flag"]]
        A.callout("<b>Possible adverse event: route to safety review.</b> Companies must collect and report adverse events "
                  "they learn about, including from field conversations. Demo rule: forward within 1 business day.<br>"
                  + "<br>".join(f"• “{s['sentence']}” (ADE probability {s['prob']:.2f})" for s in flagged), "warn")
    else:
        A.callout("No adverse event detected. The detector is tuned for ≥ 90% recall, so a clear note is a good sign, "
                  "but not a guarantee.")

    st.markdown("#### Highlighted note")
    st.html(N.highlight_html(note.strip(), r["entities"]))
    st.caption("Violet = drug · coral = adverse event · amber = dose (BiomedBERT NER, notebook 12). Hover a tag for its confidence.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Side-effect context")
        if r["ae_mode"]:
            st.markdown(f"**{AE_TEXT[r['ae_mode']]}**  ·  confidence {r['ae_mode_probs'][r['ae_mode']]:.0%}")
            st.caption("BiomedBERT, notebook 11 (4 classes: none / concern / reported / negated)")
    with c2:
        st.markdown("#### Objections raised")
        if r["objections"]:
            st.html(" ".join(f'<span class="aur-pill" style="background:#EFEAFF;color:#4B32C8;margin:2px">{OBJ_TEXT[o["objection"]]} · {o["prob"]:.0%}</span>'
                             for o in r["objections"]))
        else:
            st.markdown("None detected.")
        st.caption("TF-IDF + logistic regression, notebook 11's best model for objections")

    with st.expander("Sentence-level ADE scores"):
        st.dataframe(pd.DataFrame(r["ade_sentences"]), hide_index=True,
                     column_config={"prob": st.column_config.ProgressColumn("ADE probability", min_value=0, max_value=1, format="%.2f")})

st.caption("Models trained on public ADE Corpus v2 and synthetic visit notes; expect lower accuracy on real notes. "
           "Never enter patient-identifying information.")
