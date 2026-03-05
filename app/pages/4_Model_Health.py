import streamlit as st
from ui.styles import apply_styles
from ui.data_access import get_latest_date, load_predictions

apply_styles()
st.set_page_config(page_title="FCA · Model Health", page_icon="🩺", layout="wide")

DATA_DIR = "data"
sport = st.session_state.get("sport", "ncaab")
latest_date = get_latest_date(DATA_DIR, sport)

st.markdown(f"### Model Health · {sport.upper()} · {latest_date or ''}")

if not latest_date:
    st.error("Missing latest.json for this sport.")
    st.stop()

preds = load_predictions(DATA_DIR, sport, latest_date, model_version="baseline_v1")
if not preds:
    st.error("Missing predictions for latest date.")
    st.stop()

p = preds.get("predictions", [])
count = len(p)
with_odds = sum(1 for x in p if x.get("odds_event_id") is not None)
has_market = sum(1 for x in p if (x.get("market_edges") or x.get("market") or {}).get("has_market"))

c1, c2, c3 = st.columns(3)
c1.metric("Predictions", str(count))
c2.metric("Joined Odds (event_id)", f"{with_odds}/{count}")
c3.metric("Markets Present", f"{has_market}/{count}")

st.info("If markets are missing, it’s usually scrape timing. The UI is wired correctly either way.")
