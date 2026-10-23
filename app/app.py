"""GLP-1 Launch Intelligence · analyst dashboard.

Run from the project root:   streamlit run app/app.py
Data: app/data/*.parquet, built by  python -m glp1_intel.app_data
"""
import streamlit as st

st.set_page_config(page_title="GLP-1 Launch Intelligence", page_icon="◉", layout="wide")

pages = {
    "Analyst view": [
        st.Page("views/home.py", title="Overview", icon=":material/space_dashboard:", default=True),
        st.Page("views/market.py", title="Market", icon=":material/bar_chart:"),
        st.Page("views/targeting.py", title="Targeting", icon=":material/target:"),
        st.Page("views/doctor.py", title="Doctor 360", icon=":material/person_search:"),
        st.Page("views/safety.py", title="Safety signals", icon=":material/health_and_safety:"),
    ],
    "AI assistant": [
        st.Page("views/ask_ai.py", title="Ask AI", icon=":material/smart_toy:"),
    ],
}
nav = st.navigation(pages)

with st.sidebar:
    st.markdown("### ◉ GLP-1 Launch Intelligence")
    st.caption("Open-source pharma commercial analytics on public US data")
    st.markdown("---")

nav.run()

with st.sidebar:
    st.markdown("---")
    st.caption("Coming next: Voice of doctors · Sales-rep view")
    st.caption("Public + synthetic data only. Not affiliated with any pharmaceutical company. Not medical advice.")
