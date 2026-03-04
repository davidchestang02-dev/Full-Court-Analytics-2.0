from __future__ import annotations
import sys
from pathlib import Path
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ui.data_access import load_predictions
from app.ui.components import metric_row

st.title("🔎 Game Detail")

data_dir = st.session_state.get("data_dir", "data")
sport = st.session_state.get("sport", "ncaab")
date = st.session_state.get("date", "")

pred = load_predictions(data_dir, sport, date, model_version="baseline_v1")
if not pred:
    st.error("No predictions loaded.")
    st.stop()

rows = pred.get("predictions", [])
options = [r.get("matchup_title") for r in rows]
pick = st.selectbox("Select a game", options=options)

g = next(r for r in rows if r.get("matchup_title") == pick)
proj = g.get("proj") or {}
market = g.get("market") or {}
teams = g.get("teams") or {}

metric_row([
    ("Home", teams.get("home", "—"), ""),
    ("Away", teams.get("away", "—"), ""),
    ("Time", g.get("time_local", "—"), ""),
])

st.divider()
st.subheader("Projection")
metric_row([
    ("Proj Total", f"{proj.get('proj_total', 0):.1f}" if proj.get("proj_total") is not None else "—", proj.get("poss_source", "")),
    ("Proj Home", f"{proj.get('proj_home', 0):.1f}" if proj.get("proj_home") is not None else "—", ""),
    ("Proj Away", f"{proj.get('proj_away', 0):.1f}" if proj.get("proj_away") is not None else "—", ""),
    ("Proj Spread (Home)", f"{proj.get('proj_spread_home', 0):.1f}" if proj.get("proj_spread_home") is not None else "—", ""),
])

st.subheader("Market")
if not market.get("has_market"):
    st.warning("No market lines available for this game in the loaded odds snapshot.")
else:
    metric_row([
        ("Market Total", f"{market.get('market_total'):.1f}", ""),
        ("Market Spread (Home)", f"{market.get('market_spread_home'):.1f}", ""),
        ("Total Edge", f"{market.get('total_edge'):+.2f}", "proj_total - market_total"),
        ("Spread Edge", f"{market.get('spread_edge'):+.2f}", "proj_spread_home - market_spread_home"),
    ])

st.caption(f"Odds Event ID: {g.get('odds_event_id')}")
