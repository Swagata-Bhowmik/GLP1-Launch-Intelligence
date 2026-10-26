import streamlit as st

# The landing page fills the whole window: hide Streamlit's own menu, padding and footer here; the landing
# site (app/static/site/index.html) has its own navigation, and its cards open the tool pages.
# The frame address is resolved by the browser relative to the app's own URL, because Streamlit Community Cloud
# serves the app (and its static files) under /~/+/ while a local run serves them at the root.
st.html("""
<style>
  [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"] { display: none !important; }
  .block-container, [data-testid="stMainBlockContainer"] { padding: 0 !important; max-width: 100% !important; }
  [data-testid="stApp"] { overflow: hidden; }
  #ll-landing { position: fixed; inset: 0; width: 100vw; height: 100vh; height: 100dvh; border: 0; z-index: 999991; background: #F4F8FF; }
</style>
<script>
(() => {
  document.getElementById("ll-landing")?.remove();
  const f = document.createElement("iframe");
  f.id = "ll-landing";
  f.title = "LaunchLens";
  f.src = new URL("app/static/site/index.html?v=7", document.baseURI).href;
  document.body.appendChild(f);
  // the landing page's buttons ask this page to open a tool page (frames can't navigate their parent on Cloud)
  if (!window.__llNav) {
    window.__llNav = true;
    const pages = ["guide", "market", "targeting", "doctor", "safety", "home", "rep_brief", "rep_note", "ask_ai",
                   "notebooks", "decisions"];
    window.addEventListener("message", (e) => {
      const d = e.data || {};
      if (e.origin === location.origin && d.launchlens === "open" && pages.includes(d.page))
        location.href = new URL(d.page, document.baseURI).href;
    });
  }
  // leaving the Home page (Streamlit switches pages without a reload) must remove the full-screen frame
  const path = location.pathname;
  const watch = setInterval(() => { if (location.pathname !== path) { f.remove(); clearInterval(watch); } }, 300);
})();
</script>
""", unsafe_allow_javascript=True)
