from __future__ import annotations
import sys
from pathlib import Path
import streamlit as st
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ui.data_access import load_results
from app.ui.components import metric_row

st.title("✅ Results")

data_dir = st.session_state.get("data_dir", "data")
sport = st.session_state.get("sport", "ncaab")
date = st.session_state.get("date", "")

res = load_results(data_dir, sport, date)
if not res:
    st.info("No results file found yet. Run your results pipeline after games go final.")
    st.stop()

rows = res.get("games", []) or res.get("results", []) or []

df = pd.DataFrame(rows)
st.subheader("Summary")

# These keys depend on your results schema — safe handling:
ats = df["ats_win"].mean() if "ats_win" in df.columns else None
ou = df["ou_win"].mean() if "ou_win" in df.columns else None
su = df["su_win"].mean() if "su_win" in df.columns else None

metric_row([
    ("Games Graded", f"{len(df)}", "Finals graded using closing lines"),
    ("SU%", f"{(su*100):.1f}%" if su is not None else "—", ""),
    ("ATS%", f"{(ats*100):.1f}%" if ats is not None else "—", ""),
    ("O/U%", f"{(ou*100):.1f}%" if ou is not None else "—", ""),
])

st.subheader("Game Results")
st.dataframe(df, use_container_width=True, hide_index=True)
