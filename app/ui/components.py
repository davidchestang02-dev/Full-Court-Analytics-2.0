from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import streamlit as st

def _btn_key(prefix: str, slug: str) -> str:
    return f"{prefix}__{slug}"

def set_selected_game(slug: str):
    st.session_state["selected_slug"] = slug
    st.session_state["view"] = "detail"
    try:
        st.switch_page("pages/2_Game_Detail.py")
    except Exception:
        # fallback if switch_page isn't available in your Streamlit version
        st.session_state["view"] = "detail"

def top_play_card(game: Dict[str, Any], rank: int):
    slug = game.get("slug", "")
    title = game.get("matchup_title", slug)
    t = game.get("time_local") or ""
    proj = game.get("proj") or {}
    edges = game.get("market_edges") or game.get("market") or {}
    spread_edge = edges.get("spread_edge")
    total_edge = edges.get("total_edge")

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f'<div class="topplay-title">#{rank} · {title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="muted">{t}</div>', unsafe_allow_html=True)

    chips = []
    if proj.get("ok"):
        chips.append(f"Proj Total: {proj.get('proj_total', 0):.1f}")
        chips.append(f"Proj Spread(H): {proj.get('proj_spread_home', 0):.1f}")
    if spread_edge is not None:
        chips.append(f"Spread Edge: {spread_edge:+.2f}")
    if total_edge is not None:
        chips.append(f"Total Edge: {total_edge:+.2f}")

    if chips:
        st.markdown('<div class="metric-row">', unsafe_allow_html=True)
        for c in chips[:5]:
            st.markdown(f'<div class="metric-chip">{c}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
    if st.button("Open game", key=_btn_key("open_top", slug), use_container_width=True):
        set_selected_game(slug)

def slate_row(game: Dict[str, Any]):
    slug = game.get("slug", "")
    title = game.get("matchup_title", slug)
    t = game.get("time_local") or ""
    edges = game.get("market_edges") or game.get("market") or {}
    badge_txt = "No market"
    if edges.get("has_market"):
        se = edges.get("spread_edge")
        te = edges.get("total_edge")
        parts = []
        if se is not None: parts.append(f"S {se:+.2f}")
        if te is not None: parts.append(f"T {te:+.2f}")
        badge_txt = " · ".join(parts) if parts else "Market"

    st.markdown(
        f"""
        <div class="row">
          <div class="row-left">
            <div class="row-title">{title}</div>
            <div class="row-sub">{t}</div>
          </div>
          <div class="badge">{badge_txt}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("View", key=_btn_key("open_row", slug)):
        set_selected_game(slug)

def stat_compare_row(stat_name: str, away_val: float, home_val: float, fmt: str = "{:.3f}"):
    # determine winner for coloring
    if away_val == home_val:
        away_w, home_w = 0.5, 0.5
        away_color = "rgba(46, 204, 113, 0.65)"
        home_color = "rgba(46, 204, 113, 0.65)"
    else:
        mx = max(away_val, home_val)
        mn = min(away_val, home_val)
        # bar widths within the track
        away_w = 0.12 + 0.88 * (away_val - mn) / (mx - mn)
        home_w = 0.12 + 0.88 * (home_val - mn) / (mx - mn)
        away_color = "rgba(46, 204, 113, 0.75)" if away_val > home_val else "rgba(231, 76, 60, 0.75)"
        home_color = "rgba(46, 204, 113, 0.75)" if home_val > away_val else "rgba(231, 76, 60, 0.75)"

    st.markdown(
        f"""
        <div class="statgrid">
          <div class="statval">{fmt.format(away_val)}</div>
          <div>
            <div class="statname">{stat_name}</div>
            <div class="barwrap">
              <div class="bar" style="width:{away_w*50:.1f}%; background:{away_color};"></div>
              <div class="bar" style="width:{home_w*50:.1f}%; background:{home_color};"></div>
            </div>
          </div>
          <div class="statval">{fmt.format(home_val)}</div>
        </div>
        """,
        unsafe_allow_html=True
    )
