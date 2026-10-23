"""LaunchLens (GLP-1 Launch Intelligence) · Streamlit app.

Front page = the scrolling LaunchLens landing site (app/static/site/, served by Streamlit's static file serving).
Tool pages sit behind a slim glass menu at the top (no sidebar).

Run from the project root:   streamlit run app/app.py
Data: app/data/*.parquet, built by  python -m glp1_intel.app_data
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))   # works without `pip install -e .` (cloud)
from glp1_intel import cloud  # noqa: E402

st.set_page_config(page_title="LaunchLens · GLP-1 market intelligence", page_icon="◉", layout="wide",
                   initial_sidebar_state="collapsed")


@st.cache_resource(show_spinner="First start: downloading data and models from Hugging Face (about 2 minutes)…")
def _assets():
    return cloud.ensure_assets()


_assets()
st.logo(str(Path(__file__).parent / "static" / "site" / "assets" / "logo.svg"), size="large")

pages = {
    "": [st.Page("views/landing.py", title="Home", icon=":material/home:", default=True),
         st.Page("views/ask_ai.py", title="Ask AI", icon=":material/smart_toy:")],
    "Analyst": [
        st.Page("views/market.py", title="Market", icon=":material/bar_chart:"),
        st.Page("views/targeting.py", title="Find doctors", icon=":material/target:"),
        st.Page("views/doctor.py", title="Doctor 360", icon=":material/person_search:"),
        st.Page("views/safety.py", title="Safety", icon=":material/health_and_safety:"),
        st.Page("views/home.py", title="Key numbers", icon=":material/space_dashboard:"),
    ],
    "Sales rep": [
        st.Page("views/rep_brief.py", title="Pre-visit brief", icon=":material/assignment_ind:"),
        st.Page("views/rep_note.py", title="Log a visit", icon=":material/edit_note:"),
    ],
}
nav = st.navigation(pages, position="top")
nav.run()

if nav.title != "Home":
    st.html('<div class="ll-foot">Public + synthetic data only · Not affiliated with any pharmaceutical company · '
            'Not medical advice · <a href="/" target="_self">LaunchLens home</a></div>')
