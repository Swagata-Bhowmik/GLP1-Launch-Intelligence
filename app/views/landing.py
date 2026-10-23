import streamlit as st

# The landing page fills the whole window: hide Streamlit's own menu, padding and footer here; the landing
# site (app/static/site/index.html) has its own navigation, and its cards open the tool pages.
st.html("""
<style>
  [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"] { display: none !important; }
  .block-container { padding: 0 !important; max-width: 100% !important; }
  [data-testid="stMainBlockContainer"] { padding: 0 !important; }
  [data-testid="stAppViewContainer"] > section, [data-testid="stMain"] { padding: 0 !important; }
  .st-key-landing iframe { height: 100vh !important; height: 100dvh !important; width: 100% !important; border: 0; display: block; }
  .st-key-landing { gap: 0 !important; }
  [data-testid="stApp"] { overflow: hidden; }
</style>
""")

with st.container(key="landing"):
    st.iframe("/app/static/site/index.html", height=900)
