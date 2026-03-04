import streamlit as st
import json
from pathlib import Path

st.title("Today")

sport = st.selectbox("Sport", ["ncaab","nba"], index=0)
date_str = st.text_input("Date (YYYY-MM-DD)", value="2026-03-03")

pred_path = Path("data") / sport / date_str / "predictions" / "baseline_v1.json"
if not pred_path.exists():
    st.warning(f"No predictions found at: {pred_path}")
    st.stop()

data = json.loads(pred_path.read_text(encoding="utf-8"))
preds = data["predictions"]

# quick table
rows = []
for p in preds:
    teams = p["teams"]
    proj = p["proj"]
    mkt = p["market"]
    if not proj.get("ok"):
        continue
    rows.append({
        "Away": teams["away"],
        "Home": teams["home"],
        "Proj Home": round(proj["proj_home"], 1),
        "Proj Away": round(proj["proj_away"], 1),
        "Proj Spread(H)": round(proj["proj_spread_home"], 1),
        "Proj Total": round(proj["proj_total"], 1),
        "Mkt Spread(H)": mkt.get("market_spread_home"),
        "Spread Edge": (round(mkt["spread_edge"], 2) if mkt.get("has_market") else None),
        "Mkt Total": mkt.get("market_total"),
        "Total Edge": (round(mkt["total_edge"], 2) if mkt.get("has_market") else None),
    })

st.dataframe(rows, use_container_width=True)
