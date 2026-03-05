import streamlit as st
from ui.styles import apply_styles

st.set_page_config(
    page_title="Full Court Analytics",
    page_icon="images/fca_logo.png",
    layout="wide",
)

apply_styles()

if "sport" not in st.session_state:
    st.session_state["sport"] = "ncaab"
if "view" not in st.session_state:
    st.session_state["view"] = "today"
if "selected_slug" not in st.session_state:
    st.session_state["selected_slug"] = None

st.markdown('<div class="app-title">Full Court Analytics</div>', unsafe_allow_html=True)
st.markdown('<div class="app-subtitle">Model-Driven Betting Intelligence</div>', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns([1, 1, 1, 3])
with c1:
    if st.button("Today", use_container_width=True):
        st.switch_page("pages/1_Today.py")
with c2:
    if st.button("Game Detail", use_container_width=True):
        st.switch_page("pages/2_Game_Detail.py")
with c3:
    if st.button("Results", use_container_width=True):
        st.switch_page("pages/3_Results.py")
with c4:
    sport = st.selectbox("Sport", ["ncaab", "nba"], index=0 if st.session_state["sport"] == "ncaab" else 1)
    st.session_state["sport"] = sport

st.info("Use the pages in /app/pages. Sidebar is intentionally hidden for a cleaner product UI.")
