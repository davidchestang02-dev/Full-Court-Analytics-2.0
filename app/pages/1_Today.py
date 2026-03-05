import streamlit as st
from ui.styles import apply_styles
from ui.data_access import get_latest_date, load_predictions, load_combined_daily
from ui.components import top_play_card, slate_row, set_selected_game

apply_styles()
st.set_page_config(page_title="FCA · Today", page_icon="🏀", layout="wide")

DATA_DIR = "data"
sport = st.session_state.get("sport", "ncaab")
latest_date = get_latest_date(DATA_DIR, sport)

st.markdown(f"### Today · {sport.upper()} · {latest_date or 'No latest.json found'}")

if not latest_date:
    st.error(f"Missing {DATA_DIR}/{sport}/latest.json. Run the scrapers first.")
    st.stop()

preds = load_predictions(DATA_DIR, sport, latest_date, model_version="baseline_v1")
combined = load_combined_daily(DATA_DIR, sport, latest_date)

if not preds or "predictions" not in preds:
    st.error("Missing predictions file. Run: python model_pipeline.py --sport ... --date ...")
    st.stop()

games = preds["predictions"]

# Build a clean display label list
labels = []
slug_to_game = {}
for g in games:
    slug = g.get("slug")
    label = f"{g.get('time_local', '')} · {g.get('matchup_title', slug)}"
    labels.append(label)
    slug_to_game[label] = g

# Dropdown selector (your request: NO sliders)
sel = st.selectbox("Matchup", labels, index=0)
if st.button("Open selected matchup", use_container_width=True):
    set_selected_game(slug_to_game[sel].get("slug"))

# Rank “Top Plays” using abs edges (simple + stable)
def score_top(g):
    e = g.get("market_edges") or g.get("market") or {}
    if not e.get("has_market"):
        return -1e9
    se = e.get("spread_edge") or 0.0
    te = e.get("total_edge") or 0.0
    return abs(se) * 1.0 + abs(te) * 0.8

ranked = sorted(games, key=score_top, reverse=True)

st.markdown("### Top Plays")
top = [g for g in ranked if (g.get("market_edges") or g.get("market") or {}).get("has_market")][:6]
if not top:
    st.warning("No market edges found (likely market lines were missing at scrape time).")
else:
    cols = st.columns(3)
    for i, g in enumerate(top, start=1):
        with cols[(i - 1) % 3]:
            top_play_card(g, i)

st.markdown("### Full Slate")
# Show the rest (including non-top plays)
for g in ranked[:40]:
    slate_row(g)
