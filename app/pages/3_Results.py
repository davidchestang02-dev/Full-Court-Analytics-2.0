import streamlit as st
from ui.styles import apply_styles
from ui.data_access import list_available_dates, load_results

apply_styles()
st.set_page_config(page_title="FCA · Results", page_icon="✅", layout="wide")

DATA_DIR = "data"
sport = st.session_state.get("sport", "ncaab")

st.markdown(f"### Results · {sport.upper()}")

dates = list_available_dates(DATA_DIR, sport)
if not dates:
    st.warning("No dated folders found yet.")
    st.stop()

date_sel = st.selectbox("Date", dates, index=0)
res = load_results(DATA_DIR, sport, date_sel)
if not res:
    st.warning("No final_results.json found for that date.")
    st.stop()

games = res.get("games", []) or res.get("results", []) or []

st.markdown(f"**Games graded:** {len(games)}")
for g in games[:50]:
    title = g.get("matchup_title", g.get("slug"))
    closing = g.get("closing", {})
    grading = g.get("grading", {})
    su = grading.get("su", {}).get("winner")
    ats = grading.get("ats", {}).get("ats_winner")
    ou = grading.get("ou", {}).get("ou_result")
    st.markdown(
        f"- **{title}** · SU: **{su}** · ATS: **{ats}** · O/U: **{ou}**"
    )
