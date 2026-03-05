from __future__ import annotations

import streamlit as st
from datetime import date

from ui.styles import inject_global_styles, set_app_background
from ui.data_access import (
    get_available_dates,
    load_games_for_date,
    load_game_detail_bundle,
)
from ui.components import (
    render_top_nav,
    render_landing,
    render_today,
    render_game_detail,
    render_results,
    render_model_health,
)

APP_TITLE = "Full Court Analytics"
APP_SUBTITLE = "AI-driven slate projections + market edge detection (automated pipeline)"

st.set_page_config(
    page_title="Full Court Analytics",
    page_icon="images/fca_logo.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_global_styles()


def _init_state():
    if "route" not in st.session_state:
        st.session_state.route = "landing"  # landing | today | detail | results | health
    if "nav_stack" not in st.session_state:
        st.session_state.nav_stack = []  # stack of (route, payload)
    if "sport" not in st.session_state:
        st.session_state.sport = None
    if "selected_date" not in st.session_state:
        st.session_state.selected_date = None
    if "selected_slug" not in st.session_state:
        st.session_state.selected_slug = None


def go(route: str, **payload):
    # push current to stack
    st.session_state.nav_stack.append(
        (st.session_state.route, {
            "sport": st.session_state.sport,
            "selected_date": st.session_state.selected_date,
            "selected_slug": st.session_state.selected_slug,
        })
    )
    st.session_state.route = route
    for k, v in payload.items():
        setattr(st.session_state, k, v)
    st.rerun()


def back():
    if not st.session_state.nav_stack:
        st.session_state.route = "landing"
        st.session_state.sport = None
        st.session_state.selected_date = None
        st.session_state.selected_slug = None
        st.rerun()

    prev_route, prev_payload = st.session_state.nav_stack.pop()
    st.session_state.route = prev_route
    st.session_state.sport = prev_payload.get("sport")
    st.session_state.selected_date = prev_payload.get("selected_date")
    st.session_state.selected_slug = prev_payload.get("selected_slug")
    st.rerun()


_init_state()

# Background only on landing to keep it premium
if st.session_state.route == "landing":
    set_app_background("images/fca_background_1.png")
else:
    set_app_background(None)

# Always show a clean top nav (NOT Streamlit sidebar)
render_top_nav(
    title=APP_TITLE,
    subtitle=APP_SUBTITLE,
    show_back=(st.session_state.route != "landing"),
    on_back=back,
    on_home=lambda: go("landing", sport=None, selected_date=None, selected_slug=None),
    on_today=lambda: go("today"),
    on_results=lambda: go("results"),
    on_health=lambda: go("health"),
)

# ---------- ROUTES ----------
if st.session_state.route == "landing":
    # landing chooses sport + date
    available = get_available_dates(st.session_state.sport)
    default_date = st.session_state.selected_date or (available[-1] if available else date.today().isoformat())
    render_landing(
        logo_path="images/fca_logo.png",
        sport=st.session_state.sport,
        default_date=default_date,
        available_dates=available,
        on_select_sport=lambda sport: go("landing", sport=sport, selected_date=default_date),
        on_open_today=lambda sport, date_str: go("today", sport=sport, selected_date=date_str),
    )

elif st.session_state.route == "today":
    if not st.session_state.sport:
        go("landing")
    if not st.session_state.selected_date:
        # fall back to latest available or today
        available = get_available_dates(st.session_state.sport)
        st.session_state.selected_date = available[-1] if available else date.today().isoformat()

    games_bundle = load_games_for_date(st.session_state.sport, st.session_state.selected_date)

    render_today(
        sport=st.session_state.sport,
        date_str=st.session_state.selected_date,
        games_bundle=games_bundle,
        on_change_date=lambda new_date: go("today", selected_date=new_date),
        on_open_game=lambda slug: go("detail", selected_slug=slug),
    )

elif st.session_state.route == "detail":
    if not st.session_state.sport or not st.session_state.selected_date or not st.session_state.selected_slug:
        go("today")

    bundle = load_game_detail_bundle(
        sport=st.session_state.sport,
        date_str=st.session_state.selected_date,
        slug=st.session_state.selected_slug,
    )

    render_game_detail(
        sport=st.session_state.sport,
        date_str=st.session_state.selected_date,
        bundle=bundle,
        on_back_to_today=lambda: go("today"),
    )

elif st.session_state.route == "results":
    if not st.session_state.sport:
        # results can be opened from landing as well
        go("landing")
    available = get_available_dates(st.session_state.sport)
    default_date = st.session_state.selected_date or (available[-1] if available else date.today().isoformat())
    st.session_state.selected_date = default_date

    render_results(
        sport=st.session_state.sport,
        date_str=st.session_state.selected_date,
        on_change_date=lambda d: go("results", selected_date=d),
        on_open_game=lambda slug: go("detail", selected_slug=slug),
    )

elif st.session_state.route == "health":
    render_model_health()
