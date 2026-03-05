import streamlit as st
from ui.styles import apply_styles
from ui.data_access import get_latest_date, load_predictions
from ui.components import stat_compare_row

apply_styles()
st.set_page_config(page_title="FCA · Game Detail", page_icon="🏀", layout="wide")

DATA_DIR = "data"
sport = st.session_state.get("sport", "ncaab")
latest_date = get_latest_date(DATA_DIR, sport)

st.markdown(f"### Game Detail · {sport.upper()} · {latest_date or ''}")

preds = load_predictions(DATA_DIR, sport, latest_date, model_version="baseline_v1") if latest_date else None
if not preds:
    st.error("No predictions loaded.")
    st.stop()

slug = st.session_state.get("selected_slug")
games = preds.get("predictions", [])
game = next((g for g in games if g.get("slug") == slug), None)

if not game:
    st.warning("No game selected yet. Go to Today and click a game.")
    st.stop()

title = game.get("matchup_title", slug)
teams = game.get("teams") or {}
away = (teams.get("away") or "Away")
home = (teams.get("home") or "Home")
t = game.get("time_local") or ""

st.markdown(f"## {title}")
st.caption(f"{away} @ {home} · {t}")

proj = game.get("proj") or {}
edges = game.get("market_edges") or game.get("market") or {}

c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Proj Total", f"{proj.get('proj_total', 0):.1f}" if proj.get("ok") else "—")
with c2:
    st.metric("Proj Spread (Home)", f"{proj.get('proj_spread_home', 0):.1f}" if proj.get("ok") else "—")
with c3:
    st.metric("Market Available", "Yes" if edges.get("has_market") else "No")

# --------- STAT TABLE (TeamRankings-style visual) ----------
st.markdown("### Team Comparison (visual)")

# For now: derive from proj + market if present (stable)
# Then you can expand later to include more features directly from combined_daily.
stat_rows = []

# Some quick reliable items
if proj.get("ok"):
    stat_rows.append(("Projected PPP", float(proj.get("ppp_away", 0.0)), float(proj.get("ppp_home", 0.0)), "{:.3f}"))
    stat_rows.append(("Projected Score", float(proj.get("proj_away", 0.0)), float(proj.get("proj_home", 0.0)), "{:.1f}"))
    stat_rows.append(("Projected Margin (Home)", float(-proj.get("proj_spread_home", 0.0)), float(proj.get("proj_spread_home", 0.0)), "{:+.1f}"))

if edges.get("has_market"):
    stat_rows.append(("Market Spread (Home)", float(edges.get("market_spread_home", 0.0)), float(edges.get("market_spread_home", 0.0)), "{:+.1f}"))
    stat_rows.append(("Spread Edge (Home)", float(-edges.get("spread_edge", 0.0)), float(edges.get("spread_edge", 0.0)), "{:+.2f}"))
    stat_rows.append(("Market Total", float(edges.get("market_total", 0.0)), float(edges.get("market_total", 0.0)), "{:.1f}"))
    stat_rows.append(("Total Edge", float(-edges.get("total_edge", 0.0)), float(edges.get("total_edge", 0.0)), "{:+.2f}"))

st.caption(f"{away} (left) vs {home} (right)")

for name, av, hv, fmt in stat_rows:
    stat_compare_row(name, av, hv, fmt=fmt)

st.markdown('<div class="smallnote">Next upgrade: pull more features (eFG%, TO%, ORB%, etc.) directly from combined_daily and render here.</div>', unsafe_allow_html=True)
