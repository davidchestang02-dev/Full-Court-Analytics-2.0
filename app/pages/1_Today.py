from __future__ import annotations
import sys
from pathlib import Path
import streamlit as st
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ui.data_access import load_predictions
from app.ui.components import metric_row, edge_badge

st.title("📅 Today / Slate")

data_dir = st.session_state.get("data_dir", "data")
sport = st.session_state.get("sport", "ncaab")
date = st.session_state.get("date", "")

pred = load_predictions(data_dir, sport, date, model_version="baseline_v1")

if not pred:
    st.error(f"No predictions found for {sport} on {date}. Run the pipeline first.")
    st.stop()

rows = pred.get("predictions", [])
count = len(rows)

with_odds = sum(1 for r in rows if r.get("odds_event_id") is not None)
has_market = sum(1 for r in rows if (r.get("market") or {}).get("has_market"))

metric_row([
    ("Games", f"{count}", "Total games in slate"),
    ("Matched Odds", f"{with_odds}", "Games matched to an odds event_id"),
    ("Has Market Lines", f"{has_market}", "Spread/Total lines present in odds snapshot"),
])

# Build a dataframe for sorting/filtering
table = []
for r in rows:
    mk = r.get("market") or {}
    pj = r.get("proj") or {}
    table.append({
        "matchup": r.get("matchup_title"),
        "time_local": r.get("time_local"),
        "proj_total": pj.get("proj_total"),
        "proj_spread_home": pj.get("proj_spread_home"),
        "market_total": mk.get("market_total"),
        "market_spread_home": mk.get("market_spread_home"),
        "total_edge": mk.get("total_edge"),
        "spread_edge": mk.get("spread_edge"),
        "odds_event_id": r.get("odds_event_id"),
        "slug": r.get("slug"),
    })

df = pd.DataFrame(table)

# Filters
c1, c2, c3 = st.columns([1, 1, 2])
with c1:
    show_only_lines = st.checkbox("Only show games with lines", value=False)
with c2:
    min_edge = st.number_input("Min abs edge", value=0.0, step=0.5)
with c3:
    q = st.text_input("Search matchup", value="")

if show_only_lines:
    df = df[df["market_total"].notna() | df["market_spread_home"].notna()]

if min_edge > 0:
    df = df[
        (df["spread_edge"].abs().fillna(0) >= min_edge) |
        (df["total_edge"].abs().fillna(0) >= min_edge)
    ]

if q.strip():
    df = df[df["matchup"].str.contains(q.strip(), case=False, na=False)]

# Display: quick badge columns
df_display = df.copy()
df_display["spread_edge_badge"] = df_display["spread_edge"].apply(edge_badge)
df_display["total_edge_badge"] = df_display["total_edge"].apply(edge_badge)

st.subheader("Edges (sortable)")
st.dataframe(
    df_display[[
        "time_local",
        "matchup",
        "market_spread_home",
        "proj_spread_home",
        "spread_edge_badge",
        "market_total",
        "proj_total",
        "total_edge_badge",
        "odds_event_id",
    ]].sort_values(by=["spread_edge"], key=lambda s: s.abs(), ascending=False),
    use_container_width=True,
    hide_index=True,
)
