from __future__ import annotations
import streamlit as st
from app.ui.data_access import list_dates, load_results

st.title("📈 Model Health")

data_dir = st.session_state.get("data_dir", "data")
sport = st.session_state.get("sport", "ncaab")

dates = list_dates(data_dir, sport)
dates = dates[-30:]  # last 30 available folders

if not dates:
    st.info("No historical dates found yet.")
    st.stop()

st.caption("This page becomes powerful once you have multiple days of results.")

# Placeholder: show how many result files exist
have_results = 0
for d in dates:
    if load_results(data_dir, sport, d):
        have_results += 1

st.metric("Days with results", have_results)
st.write("Next step: compute rolling ATS/O-U accuracy + calibration curves once results schema is finalized.")
