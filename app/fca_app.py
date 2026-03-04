from __future__ import annotations
import streamlit as st
from app.ui.styles import inject_global_css
from app.ui.data_access import list_available_sports, get_default_sport, get_default_date

st.set_page_config(
    page_title="Full Court Analytics",
    page_icon="images/fca_logo.png",
    layout="wide",
)

inject_global_css()

st.title("Full Court Analytics")
st.caption("Model-Driven Betting Intelligence")

# Sidebar: Global controls
with st.sidebar:
    st.header("Controls")
    sports = list_available_sports(data_dir="data")
    sport = st.selectbox("Sport", options=sports, index=sports.index(get_default_sport(sports)) if sports else 0)

    date = st.text_input("Date (YYYY-MM-DD)", value=get_default_date("data", sport))
    st.session_state["sport"] = sport
    st.session_state["date"] = date
    st.session_state["data_dir"] = "data"

st.info("Use the left sidebar to select a sport/date. Navigate pages using Streamlit's page menu.")
