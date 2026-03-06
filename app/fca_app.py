from __future__ import annotations

import streamlit as st
from datetime import date as dt_date
from typing import Any, Dict

from ui.styles import inject_global_css
from ui.data_access import (
    list_available_dates,
    load_combined_daily,
    load_predictions,
    load_results,
    merge_slate_with_preds,
)
from ui.components import (
    qp_get,
    top_nav,
    hero,
    landing_league_cards,
    game_card,
    teamrankings_bar_table,
    render_about_page,
)

LOGO_URL = "https://raw.githubusercontent.com/davidchestang02-dev/full-court-analytics/main/images/fca_logo.png"
BG_URL = "https://raw.githubusercontent.com/davidchestang02-dev/full-court-analytics/main/images/fca_background_1.png"


def main() -> None:
    inject_global_css(bg_url=BG_URL, logo_url=LOGO_URL)

    qp = qp_get()
    page = qp.get("page", "home")
    sport = qp.get("sport", "ncaab")
    date_param = qp.get("date", "")

    top_nav(LOGO_URL)
    if page != "about":
        hero("Full Court Analytics", "Model-Driven Betting Intelligence")

    if page == "home":
        render_home()
    elif page == "today":
        render_today(sport=sport, date_str=date_param)
    elif page == "game":
        render_game_detail(sport=sport, date_str=date_param, slug=qp.get("slug", ""))
    elif page == "results":
        render_results(sport=sport, date_str=date_param)
    elif page == "health":
        render_health(sport=sport)
    elif page == "about":
        render_about()
    else:
        render_home()


def render_home() -> None:
    st.markdown("### Select a league")
    landing_league_cards()


def render_about() -> None:
    render_about_page()


def render_today(sport: str, date_str: str) -> None:
    available = list_available_dates(sport)
    if not available:
        st.warning(f"No data found for sport: {sport}")
        return

    default_date = date_str if date_str in available else available[-1]

    c1, c2 = st.columns([1, 2])
    with c1:
        picked = st.date_input(
            "Date",
            value=_parse_date(default_date),
            help="Pick any date with scraped data available.",
        )
    picked_str = picked.isoformat()

    if picked_str not in available:
        st.info("That date isn't stored yet. Showing the closest available date.")
        picked_str = available[-1]

    with c2:
        st.markdown(f"**{sport.upper()} - {picked_str}**")

    combined = load_combined_daily(sport, picked_str)
    preds = load_predictions(sport, picked_str, model_version="baseline_v1")

    if not combined:
        st.warning("No combined_daily.json available for this date yet.")
        return

    slate = merge_slate_with_preds(combined, preds)
    if not slate:
        st.info("No games were found in the combined slate for this date.")
        return

    def edge_score(g: Dict[str, Any]) -> float:
        m = g.get("market") or {}
        se = m.get("spread_edge")
        te = m.get("total_edge")
        se = abs(se) if isinstance(se, (int, float)) else 0.0
        te = abs(te) if isinstance(te, (int, float)) else 0.0
        return max(se, te)

    top = sorted(slate, key=edge_score, reverse=True)[:3]

    if any(edge_score(x) > 0 for x in top):
        st.markdown("### Top Plays")
        cols = st.columns(3, gap="large")
        for i, g in enumerate(top):
            with cols[i]:
                game_card(sport=sport, date=picked_str, g=g, logo_away=None, logo_home=None)

    st.markdown("### All Games")
    matchup_labels = [f"{g['teams']['away']} @ {g['teams']['home']}  -  {g.get('time_local', '')}" for g in slate]
    selected = st.selectbox("Select a matchup", options=list(range(len(slate))), format_func=lambda i: matchup_labels[i])

    g = slate[selected]
    game_card(sport=sport, date=picked_str, g=g, logo_away=None, logo_home=None)


def render_game_detail(sport: str, date_str: str, slug: str) -> None:
    if not sport:
        st.warning("Missing sport.")
        return

    available = list_available_dates(sport)
    if not available:
        st.warning(f"No data found for sport: {sport}")
        return

    if date_str not in available:
        date_str = available[-1]

    combined = load_combined_daily(sport, date_str)
    preds = load_predictions(sport, date_str, model_version="baseline_v1")
    results = load_results(sport, date_str)

    if not combined:
        st.warning("No combined slate found.")
        return

    slate = merge_slate_with_preds(combined, preds)
    g = next((x for x in slate if x.get("slug") == slug), None)
    if not g:
        st.warning("Game not found.")
        return

    away = g["teams"]["away"]
    home = g["teams"]["home"]

    st.markdown(f"## {away} @ {home}")
    st.caption(f"{sport.upper()} - {date_str} - {g.get('time_local', '')} - {g.get('location', '')}")

    c1, c2 = st.columns([1, 1], gap="large")
    with c1:
        st.markdown("### Model Projection")
        proj = g.get("proj") or {}
        st.write(f"**Proj Total:** {proj.get('proj_total', '—')}")
        st.write(f"**Proj Spread (Home):** {proj.get('proj_spread_home', '—')}")

    with c2:
        st.markdown("### Market (Closing)")
        mk = g.get("market") or {}
        if mk.get("has_market"):
            st.write(f"**Market Total:** {mk.get('market_total', '—')}")
            st.write(f"**Market Spread (Home):** {mk.get('market_spread_home', '—')}")
            st.write(f"**Total Edge:** {mk.get('total_edge', '—')}")
            st.write(f"**Spread Edge:** {mk.get('spread_edge', '—')}")
        else:
            st.caption("No market lines stored yet for this matchup.")

    st.markdown("### Team Comparison")

    feats = g.get("features") or {}
    rows = [
        ("Off Efficiency", feats.get("key_offensive_stats.off_efficiency.uk"), feats.get("key_offensive_stats.off_efficiency.tam")),
        ("Effective FG%", feats.get("key_offensive_stats.effective_fg.uk"), feats.get("key_offensive_stats.effective_fg.tam")),
        ("Turnovers/Play", feats.get("key_offensive_stats.turnovers_play.uk"), feats.get("key_offensive_stats.turnovers_play.tam")),
        ("Off Rebound%", feats.get("key_offensive_stats.off_rebound.uk"), feats.get("key_offensive_stats.off_rebound.tam")),
        ("Def Efficiency", feats.get("key_defensive_stats.def_efficiency.uk"), feats.get("key_defensive_stats.def_efficiency.tam")),
        ("Opp eFG%", feats.get("key_defensive_stats.opp_effective_fg.uk"), feats.get("key_defensive_stats.opp_effective_fg.tam")),
    ]
    teamrankings_bar_table(away, home, rows)

    if results:
        rec = None
        if isinstance(results, dict) and "games" in results:
            rec = next((x for x in results["games"] if x.get("slug") == slug), None)
        elif isinstance(results, list):
            rec = next((x for x in results if x.get("slug") == slug), None)

        if rec:
            st.markdown("### Final / Grading")
            st.json(rec.get("grading") or {}, expanded=False)


def render_results(sport: str, date_str: str) -> None:
    available = list_available_dates(sport)
    if not available:
        st.warning(f"No data found for sport: {sport}")
        return
    if date_str not in available:
        date_str = available[-1]

    r = load_results(sport, date_str)
    st.markdown(f"## Results - {sport.upper()} - {date_str}")
    if not r:
        st.info("No final results file found for this date yet.")
        return
    st.json(r, expanded=False)


def render_health(sport: str) -> None:
    st.markdown("## Model Health")
    st.caption("Basic diagnostics: data availability, last runs, and missing artifacts.")
    dates = list_available_dates(sport)
    st.write({"sport": sport, "dates_found": len(dates), "latest_date": (dates[-1] if dates else None)})


def _parse_date(s: str) -> dt_date:
    try:
        y, m, d = s.split("-")
        return dt_date(int(y), int(m), int(d))
    except Exception:
        return dt_date.today()


if __name__ == "__main__":
    main()
