from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import streamlit as st
from .data_access import strip_rank


# ----------------- Helpers -----------------

SPORT_META = {
    "ncaab": {"name": "NCAAB", "emoji": "🏀", "desc": "College Basketball"},
    "nba":   {"name": "NBA",   "emoji": "🏀", "desc": "Pro Basketball"},
    "nhl":   {"name": "NHL",   "emoji": "🏒", "desc": "Hockey"},
    "mlb":   {"name": "MLB",   "emoji": "⚾", "desc": "Baseball"},
    "nfl":   {"name": "NFL",   "emoji": "🏈", "desc": "Football"},
}

EDGE_TOP_THRESHOLD = 2.0  # you can tune (spread points / total points)


def _img_b64(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    return base64.b64encode(p.read_bytes()).decode("utf-8")


def _safe_team_name(s: str) -> str:
    return (s or "").replace("#", "").strip()


def _team_logos_from_prediction(pred: Dict[str, Any] | None) -> Tuple[Optional[str], Optional[str]]:
    """
    If your odds snapshot has logo URLs, put them into prediction payload and use here.
    For now, we safely return None if missing.
    """
    if not pred:
        return None, None
    odds = pred.get("odds") or {}
    teams = odds.get("teams") or {}
    away_logo = teams.get("away_logo") or teams.get("away", {}).get("logo")
    home_logo = teams.get("home_logo") or teams.get("home", {}).get("logo")
    return away_logo, home_logo


def _pick_game_list(bundle) -> List[Dict[str, Any]]:
    return bundle.games if bundle and getattr(bundle, "games", None) else []


def _pred_idx(bundle) -> Dict[str, Dict[str, Any]]:
    preds = (bundle.predictions or {}).get("predictions") if bundle and bundle.predictions else []
    idx = {}
    for p in preds or []:
        slug = p.get("slug")
        if slug:
            idx[slug] = p
    return idx


def _result_idx(bundle) -> Dict[str, Dict[str, Any]]:
    arr = (bundle.results or {}).get("games") if bundle and bundle.results else []
    idx = {}
    for r in arr or []:
        slug = r.get("slug")
        if slug:
            idx[slug] = r
    return idx


def _compute_edges(pred: Dict[str, Any] | None) -> Tuple[Optional[float], Optional[float]]:
    if not pred:
        return None, None
    me = pred.get("market_edges") or pred.get("market") or {}
    if not me or not me.get("has_market"):
        return None, None
    return me.get("spread_edge"), me.get("total_edge")


def _proj_lines(pred: Dict[str, Any] | None) -> Tuple[Optional[float], Optional[float]]:
    if not pred:
        return None, None
    pr = pred.get("proj") or {}
    if not pr.get("ok"):
        return None, None
    return pr.get("proj_total"), pr.get("proj_spread_home")


# ----------------- Top nav -----------------

def render_top_nav(
    title: str,
    subtitle: str,
    show_back: bool,
    on_back: Callable[[], None],
    on_home: Callable[[], None],
    on_today: Callable[[], None],
    on_results: Callable[[], None],
    on_health: Callable[[], None],
):
    st.markdown(
        """
        <div class="fca-glass" style="margin-bottom: 14px;">
          <div style="display:flex; align-items:center; justify-content:space-between; gap:16px;">
            <div>
              <div class="fca-title">""" + title + """</div>
              <div class="fca-subtitle">""" + subtitle + """</div>
            </div>
            <div style="display:flex; gap:10px; flex-wrap:wrap; justify-content:flex-end;">
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 1], gap="small")
    with c1:
        if show_back:
            if st.button("← Back", use_container_width=True):
                on_back()
    with c2:
        if st.button("Home", use_container_width=True):
            on_home()
    with c3:
        if st.button("Today", use_container_width=True):
            on_today()
    with c4:
        if st.button("Results", use_container_width=True):
            on_results()
    with c5:
        if st.button("Model Health", use_container_width=True):
            on_health()

    st.markdown("</div></div></div>", unsafe_allow_html=True)


# ----------------- Landing -----------------

def render_landing(
    logo_path: str,
    sport: Optional[str],
    default_date: str,
    available_dates: List[str],
    on_select_sport: Callable[[str], None],
    on_open_today: Callable[[str, str], None],
):
    st.markdown('<div class="fca-glass">', unsafe_allow_html=True)

    logo_b64 = _img_b64(logo_path)
    if logo_b64:
        st.markdown(
            f"""
            <div style="display:flex; align-items:center; gap:16px;">
              <img src="data:image/png;base64,{logo_b64}" style="height:74px; width:auto;"/>
              <div>
                <div style="font-size:1.6rem; font-weight:800; letter-spacing:0.4px;">Full Court Analytics</div>
                <div class="fca-muted" style="max-width:760px;">
                  Clean slate hub → projections, edges, and results. Built to run automated every day.
                </div>
              </div>
            </div>
            <div class="fca-hr"></div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="fca-muted">Select a league:</div>', unsafe_allow_html=True)
    cols = st.columns(5, gap="small")

    order = ["ncaab", "nba", "nhl", "mlb", "nfl"]
    for i, key in enumerate(order):
        meta = SPORT_META[key]
        with cols[i]:
            label = f"{meta['emoji']} {meta['name']}"
            if st.button(label, use_container_width=True):
                on_select_sport(key)

    st.markdown('<div class="fca-hr"></div>', unsafe_allow_html=True)

    if not sport:
        st.markdown('<div class="fca-muted">Pick a league to continue.</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        return

    meta = SPORT_META.get(sport, {"name": sport.upper(), "desc": ""})
    st.markdown(f"<div class='fca-title'>{meta['name']} Hub</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='fca-muted'>{meta['desc']}</div>", unsafe_allow_html=True)

    # Date picker: allow ANY date, but also provide available dates list
    c1, c2 = st.columns([2, 1], gap="small")
    with c1:
        use_known = st.checkbox("Use available dates found in /data", value=True)
        if use_known and available_dates:
            chosen = st.selectbox("Date", options=available_dates, index=available_dates.index(default_date) if default_date in available_dates else len(available_dates)-1)
        else:
            chosen = st.date_input("Date", value=_iso_to_date(default_date)).isoformat()

    with c2:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button("Open Today →", use_container_width=True):
            on_open_today(sport, chosen)

    st.markdown("</div>", unsafe_allow_html=True)


def _iso_to_date(s: str):
    try:
        y, m, d = s.split("-")
        return __import__("datetime").date(int(y), int(m), int(d))
    except Exception:
        return __import__("datetime").date.today()


# ----------------- Today Page -----------------

def render_today(
    sport: str,
    date_str: str,
    games_bundle,
    on_change_date: Callable[[str], None],
    on_open_game: Callable[[str], None],
):
    meta = SPORT_META.get(sport, {"name": sport.upper(), "desc": ""})
    st.markdown(f"<div class='fca-title'>{meta['name']} — {date_str}</div>", unsafe_allow_html=True)
    st.markdown("<div class='fca-muted'>Top plays auto-highlight when odds exist. Slate still loads even without odds.</div>", unsafe_allow_html=True)

    # Date selector
    c1, c2, c3 = st.columns([2, 1, 1], gap="small")
    with c1:
        new_date = st.date_input("Date", value=_iso_to_date(date_str)).isoformat()
    with c2:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button("Load Date", use_container_width=True):
            on_change_date(new_date)
    with c3:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        st.caption(f"Source: **{games_bundle.source}**")

    games = _pick_game_list(games_bundle)
    pidx = _pred_idx(games_bundle)
    ridx = _result_idx(games_bundle)

    if not games:
        st.markdown("<div class='fca-card'>No games found for this date yet. (Schedule/combined not present.)</div>", unsafe_allow_html=True)
        return

    # Build top plays list
    top = []
    for g in games:
        slug = g.get("slug")
        pred = pidx.get(slug)
        se, te = _compute_edges(pred)
        score = 0
        if se is not None:
            score = max(score, abs(se))
        if te is not None:
            score = max(score, abs(te))
        if score >= EDGE_TOP_THRESHOLD:
            top.append((score, g))

    top.sort(key=lambda x: x[0], reverse=True)

    if top:
        st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
        st.markdown("<div class='fca-hr'></div>", unsafe_allow_html=True)
        st.markdown("<div class='fca-title'>Top Plays</div>", unsafe_allow_html=True)
        grid = st.columns(3, gap="small")
        for i, (_, g) in enumerate(top[:6]):
            with grid[i % 3]:
                _render_game_card(g, pidx.get(g.get("slug")), ridx.get(g.get("slug")), on_open_game, variant="top")

    # Dropdown selector for focus game (NO slider filters)
    st.markdown("<div class='fca-hr'></div>", unsafe_allow_html=True)
    st.markdown("<div class='fca-title'>Slate</div>", unsafe_allow_html=True)
    options = [(g.get("slug"), g.get("matchup_title") or "Matchup") for g in games]
    slug_by_title = {t: s for s, t in options if t}
    titles = [t for _, t in options]

    csel1, csel2 = st.columns([3, 1], gap="small")
    with csel1:
        chosen_title = st.selectbox("Select a matchup to view (shows only that game below):", titles)
        chosen_slug = slug_by_title.get(chosen_title)
    with csel2:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button("Open Game →", use_container_width=True):
            if chosen_slug:
                on_open_game(chosen_slug)

    # Render ONLY chosen game below selector
    chosen = next((g for g in games if g.get("slug") == chosen_slug), None)
    if chosen:
        st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
        _render_game_card(chosen, pidx.get(chosen_slug), ridx.get(chosen_slug), on_open_game, variant="focus")


def _render_game_card(game: Dict[str, Any], pred: Dict[str, Any] | None, res: Dict[str, Any] | None,
                      on_open_game: Callable[[str], None], variant: str):
    teams = game.get("teams") or {}
    away = _safe_team_name(teams.get("away", "Away"))
    home = _safe_team_name(teams.get("home", "Home"))
    time_local = game.get("time_local") or ""
    location = game.get("location") or ""

    proj_total, proj_spread_home = _proj_lines(pred)
    spread_edge, total_edge = _compute_edges(pred)

    # If you wire logos into prediction/odds later, use that. Otherwise show initials badges.
    away_logo, home_logo = _team_logos_from_prediction(pred)

    slug = game.get("slug") or f"{away}@{home}"

    # Card height by variant (keeps layout consistent)
    card_min_h = 210 if variant == "top" else 220 if variant == "focus" else 200

    # Wrapper: metric-card + absolute invisible button on top (no overlap hacks)
    st.markdown(f'<div class="fca-card-wrap" style="min-height:{card_min_h}px;">', unsafe_allow_html=True)

    # Invisible click layer
    st.markdown('<div class="fca-card-hitbox">', unsafe_allow_html=True)
    if st.button("open", key=f"open_{variant}_{slug}", use_container_width=True):
        on_open_game(slug)
    st.markdown('</div>', unsafe_allow_html=True)

    # Visible metric card
    st.markdown(f'<div class="metric-card" style="min-height:{card_min_h}px;">', unsafe_allow_html=True)

    # Logos row (kept minimal — if no logos yet it falls back to initials)
    st.markdown(_logo_row_html(away, home, away_logo, home_logo), unsafe_allow_html=True)

    # Keep existing matchup text
    st.markdown(f'<div class="metric-label">{away} @ {home}</div>', unsafe_allow_html=True)

    # Keep existing time/location text
    if location:
        st.markdown(f'<div class="metric-sub">{time_local} • {location}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="metric-sub">{time_local}</div>', unsafe_allow_html=True)

    # Projections
    if proj_total is not None:
        st.markdown(f'<div class="metric-value">Proj Total: {proj_total:.1f}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="metric-value">Proj Total: —</div>', unsafe_allow_html=True)

    if proj_spread_home is not None:
        st.markdown(f'<div class="metric-sub">Proj Spread (Home): {proj_spread_home:+.1f}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="metric-sub">Proj Spread (Home): —</div>', unsafe_allow_html=True)

    # Market edges (blank/dash if no odds yet)
    if spread_edge is None:
        st.markdown('<div class="metric-sub">Spread Edge: —</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="metric-sub">Spread Edge: {spread_edge:+.2f}</div>', unsafe_allow_html=True)

    if total_edge is None:
        st.markdown('<div class="metric-sub">Total Edge: —</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="metric-sub">Total Edge: {total_edge:+.2f}</div>', unsafe_allow_html=True)

    st.markdown('</div></div>', unsafe_allow_html=True)


def _edge_badge(label: str, val: float) -> str:
    # green if positive edge (model > market), red if negative
    glow = "rgba(0,255,160,0.25)" if val > 0 else "rgba(255,80,80,0.22)"
    border = "rgba(0,255,160,0.35)" if val > 0 else "rgba(255,80,80,0.30)"
    return f"""
    <div style="border:1px solid {border}; background:{glow}; padding:10px 12px; border-radius:14px; margin-bottom:8px;">
      <div class="fca-muted" style="font-size:0.85rem;">{label}</div>
      <div style="font-size:1.15rem; font-weight:900;">{val:+.2f}</div>
    </div>
    """


def _logo_row_html(away: str, home: str, away_logo: Optional[str], home_logo: Optional[str]) -> str:
    def badge(text: str) -> str:
        initials = "".join([w[0] for w in text.split()[:2]]).upper()
        return f"<div style='height:42px; width:42px; border-radius:12px; background:rgba(255,255,255,0.08); display:flex; align-items:center; justify-content:center; font-weight:900;'>{initials}</div>"

    def img(url: str) -> str:
        return f"<img src='{url}' style='height:42px; width:42px; border-radius:12px; object-fit:contain; background:rgba(255,255,255,0.06); padding:6px;'/>"

    a = img(away_logo) if away_logo else badge(away)
    h = img(home_logo) if home_logo else badge(home)
    return f"""
    <div style="display:flex; align-items:center; gap:10px;">
      {a}
      <div class="fca-muted" style="font-weight:900;">@</div>
      {h}
    </div>
    """


# ----------------- Game Detail -----------------

def render_game_detail(
    sport: str,
    date_str: str,
    bundle: Dict[str, Any],
    on_back_to_today: Callable[[], None],
):
    base = bundle.get("base") or {}
    pred = bundle.get("prediction") or {}
    res = bundle.get("result") or {}

    teams = (base.get("teams") or (pred.get("teams") if pred else {}) or {})
    away = _safe_team_name(teams.get("away", "Away"))
    home = _safe_team_name(teams.get("home", "Home"))

    st.markdown(f"<div class='fca-title'>{away} @ {home}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='fca-muted'>{sport.upper()} • {date_str}</div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1, 1], gap="small")
    if c1.button("← Back to Today", use_container_width=True):
        on_back_to_today()

    # Header scoreboard style
    st.markdown("<div class='fca-hr'></div>", unsafe_allow_html=True)

    proj_total, proj_spread_home = _proj_lines(pred)
    se, te = _compute_edges(pred)

    left, right = st.columns([1, 1], gap="small")

    with left:
        st.markdown('<div class="fca-card">', unsafe_allow_html=True)
        st.markdown("<div class='fca-title'>Model Projection</div>", unsafe_allow_html=True)
        if proj_total is None:
            st.markdown("<div class='fca-muted'>Projections pending for this date.</div>", unsafe_allow_html=True)
        else:
            pr = pred.get("proj") or {}
            st.markdown(f"<div style='font-size:2.0rem; font-weight:900;'>{home} {pr.get('proj_home',0):.0f} — {away} {pr.get('proj_away',0):.0f}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='fca-muted'>Proj Total: {proj_total:.1f} • Proj Spread (Home): {proj_spread_home:+.1f}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="fca-card">', unsafe_allow_html=True)
        st.markdown("<div class='fca-title'>Market (Closing)</div>", unsafe_allow_html=True)
        me = pred.get("market_edges") or pred.get("market") or {}
        if not me or not me.get("has_market"):
            st.markdown("<div class='fca-muted'>No market lines stored yet for this matchup.</div>", unsafe_allow_html=True)
        else:
            st.markdown(_edge_badge("Spread Edge", float(me.get("spread_edge"))), unsafe_allow_html=True)
            st.markdown(_edge_badge("Total Edge", float(me.get("total_edge"))), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Results panel if present
    if res:
        st.markdown("<div class='fca-hr'></div>", unsafe_allow_html=True)
        st.markdown('<div class="fca-card">', unsafe_allow_html=True)
        st.markdown("<div class='fca-title'>Final / Grading</div>", unsafe_allow_html=True)
        final = res.get("final") or {}
        grading = res.get("grading") or {}
        if final:
            st.markdown(f"<div style='font-size:1.35rem; font-weight:900;'>Final: {away} {final.get('away')} — {home} {final.get('home')}</div>", unsafe_allow_html=True)
        if grading:
            su = grading.get("su") or {}
            ats = grading.get("ats") or {}
            ou = grading.get("ou") or {}
            st.markdown(f"<div class='fca-muted'>SU: {su.get('winner','-')} • ATS: {ats.get('ats_winner','-')} • O/U: {ou.get('ou_result','-')}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # TeamRankings-style stat bars (from base['features'])
    feats = base.get("features") or {}
    if feats:
        st.markdown("<div class='fca-hr'></div>", unsafe_allow_html=True)
        st.markdown("<div class='fca-title'>Team Comparison</div>", unsafe_allow_html=True)
        st.markdown("<div class='fca-muted'>Green = advantage, Red = disadvantage (stat-aware).</div>", unsafe_allow_html=True)
        _render_stat_bars(base, away, home)


def _render_stat_bars(base: Dict[str, Any], away_name: str, home_name: str):
    feats = base.get("features") or {}

    # Detect tokens like ".uk" ".tam"
    toks = set()
    prefix = "key_offensive_stats.off_efficiency."
    for k in feats.keys():
        if k.startswith(prefix):
            toks.add(k.split(".")[-1])
    toks = sorted(toks)
    if len(toks) != 2:
        st.markdown("<div class='fca-card'>Stat bars unavailable (token detection failed).</div>", unsafe_allow_html=True)
        return

    # Token mapping: use tables team_headers if present
    tables = base.get("tables") or {}
    mm = None
    for name, t in tables.items():
        if str(name).lower().startswith("matchup menu"):
            mm = t
            break
    if mm and isinstance(mm, dict) and (mm.get("team_headers") or []):
        hdrs = [str(x).strip().lower() for x in (mm.get("team_headers") or [])]
        away_tok = hdrs[0] if len(hdrs) >= 2 else toks[0]
        home_tok = hdrs[1] if len(hdrs) >= 2 else toks[1]
    else:
        away_tok, home_tok = toks[0], toks[1]

    # Stat configuration (higher_is_better flag)
    stats = [
        ("Off Efficiency", f"key_offensive_stats.off_efficiency.{away_tok}", f"key_offensive_stats.off_efficiency.{home_tok}", True),
        ("Effective FG%", f"key_offensive_stats.effective_fg.{away_tok}", f"key_offensive_stats.effective_fg.{home_tok}", True),
        ("Turnovers/Play", f"key_offensive_stats.turnovers_play.{away_tok}", f"key_offensive_stats.turnovers_play.{home_tok}", False),
        ("Off Rebound%", f"key_offensive_stats.off_rebound.{away_tok}", f"key_offensive_stats.off_rebound.{home_tok}", True),
        ("FTA/FGA", f"key_offensive_stats.fta_fga.{away_tok}", f"key_offensive_stats.fta_fga.{home_tok}", True),
        ("Def Efficiency", f"key_defensive_stats.def_efficiency.{away_tok}", f"key_defensive_stats.def_efficiency.{home_tok}", False),
        ("Opp eFG%", f"key_defensive_stats.opp_effective_fg.{away_tok}", f"key_defensive_stats.opp_effective_fg.{home_tok}", False),
        ("Opp TO/Play", f"key_defensive_stats.opp_turnovers_play.{away_tok}", f"key_defensive_stats.opp_turnovers_play.{home_tok}", True),
        ("Def Rebound%", f"key_defensive_stats.def_rebound.{away_tok}", f"key_defensive_stats.def_rebound.{home_tok}", True),
    ]

    # Header
    st.markdown(
        f"""
        <div class="fca-card">
          <div style="display:grid; grid-template-columns: 1fr 1.2fr 1fr; gap:10px; align-items:center; margin-bottom:10px;">
            <div style="font-weight:800;">{away_name}</div>
            <div class="fca-muted" style="text-align:center; font-weight:800;">STAT</div>
            <div style="font-weight:800; text-align:right;">{home_name}</div>
          </div>
        """,
        unsafe_allow_html=True,
    )

    for label, k_away, k_home, higher_better in stats:
        av = feats.get(k_away)
        hv = feats.get(k_home)
        if av is None or hv is None:
            continue

        try:
            av = float(av)
            hv = float(hv)
        except Exception:
            continue

        # Normalize into bar percent
        mn = min(av, hv)
        mx = max(av, hv)
        span = (mx - mn) if (mx - mn) != 0 else 1.0

        # For higher/lower is better stats
        if higher_better:
            away_adv = av > hv
            home_adv = hv > av
        else:
            away_adv = av < hv
            home_adv = hv < av

        away_pct = int(((av - mn) / span) * 100)
        home_pct = int(((hv - mn) / span) * 100)

        away_color = "rgba(0,255,160,0.45)" if away_adv else "rgba(255,80,80,0.35)" if home_adv else "rgba(255,255,255,0.18)"
        home_color = "rgba(0,255,160,0.45)" if home_adv else "rgba(255,80,80,0.35)" if away_adv else "rgba(255,255,255,0.18)"

        st.markdown(
            f"""
            <div style="display:grid; grid-template-columns: 1fr 1.2fr 1fr; gap:10px; align-items:center; padding:8px 0; border-top:1px solid rgba(255,255,255,0.08);">
              <div style="font-weight:800;">{av:.3f}</div>
              <div class="fca-muted" style="text-align:center; font-weight:800;">{label}</div>
              <div style="text-align:right; font-weight:800;">{hv:.3f}</div>

              <div style="height:10px; border-radius:999px; background:rgba(255,255,255,0.10); overflow:hidden;">
                <div style="width:{away_pct}%; height:10px; background:{away_color};"></div>
              </div>
              <div></div>
              <div style="height:10px; border-radius:999px; background:rgba(255,255,255,0.10); overflow:hidden;">
                <div style="width:{home_pct}%; height:10px; background:{home_color}; margin-left:auto;"></div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)


# ----------------- Results -----------------

def render_results(
    sport: str,
    date_str: str,
    on_change_date: Callable[[str], None],
    on_open_game: Callable[[str], None],
):
    st.markdown(f"<div class='fca-title'>Results — {sport.upper()} • {date_str}</div>", unsafe_allow_html=True)
    st.markdown("<div class='fca-muted'>Click any game to open detail. (Uses closing lines + grading when available.)</div>", unsafe_allow_html=True)

    c1, c2 = st.columns([2, 1], gap="small")
    with c1:
        new_date = st.date_input("Date", value=_iso_to_date(date_str)).isoformat()
    with c2:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button("Load Results", use_container_width=True):
            on_change_date(new_date)

    # results file expected at data/{sport}/{date}/results/final_results.json
    from ui.data_access import load_games_for_date
    bundle = load_games_for_date(sport, date_str)
    ridx = _result_idx(bundle)
    games = ridx.values()

    if not ridx:
        st.markdown("<div class='fca-card'>No results found for this date yet.</div>", unsafe_allow_html=True)
        return

    for g in games:
        slug = g.get("slug")
        title = g.get("matchup_title", slug)
        grading = g.get("grading") or {}
        su = (grading.get("su") or {}).get("winner")
        ats = (grading.get("ats") or {}).get("ats_winner")
        ou = (grading.get("ou") or {}).get("ou_result")

        st.markdown('<div class="fca-card-btn">', unsafe_allow_html=True)
        if st.button(" ", key=f"res_{slug}", use_container_width=True):
            on_open_game(slug)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown(
            f"""
            <div class="fca-card" style="margin-top:-58px;">
              <div class="fca-title">{title}</div>
              <div class="fca-muted">SU: {su} • ATS: {ats} • O/U: {ou}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ----------------- Model Health -----------------

def render_model_health():
    st.markdown("<div class='fca-title'>Model Health</div>", unsafe_allow_html=True)
    st.markdown("<div class='fca-muted'>Use this page to show data freshness, pipeline status, file availability, and run logs.</div>", unsafe_allow_html=True)
    st.markdown('<div class="fca-card">Coming next: last scrape time, last prediction build time, missing files, and alerts.</div>', unsafe_allow_html=True)


# ----------------- Query Param UI Helpers -----------------

def qp_get() -> Dict[str, str]:
    # streamlit >= 1.32: st.query_params is dict-like
    try:
        return dict(st.query_params)
    except Exception:
        return {}


def qp_set(**kwargs: str) -> None:
    try:
        st.query_params.clear()
        for k, v in kwargs.items():
            st.query_params[k] = v
    except Exception:
        # fallback older streamlit
        st.experimental_set_query_params(**kwargs)


def top_nav(logo_url: str) -> None:
    qp = qp_get()
    page = qp.get("page", "home")
    sport = qp.get("sport", "ncaab")
    date = qp.get("date", "")

    def link(label: str, page_to: str, extra: Dict[str, str] | None = None) -> str:
        base = {"page": page_to}
        if sport:
            base["sport"] = sport
        if date:
            base["date"] = date
        if extra:
            base.update(extra)
        href = "?" + "&".join([f"{k}={_url_escape(v)}" for k, v in base.items() if v is not None])
        active_cls = " active" if page == page_to else ""
        return f'<a class="fca-pill{active_cls}" href="{href}">{label}</a>'

    st.markdown(
        f"""
<div class="fca-nav">
  <div class="brand">
    <img src="{logo_url}" />
    <div class="brand-title">Full Court Analytics</div>
  </div>
  <div class="navlinks">
    {link("Home", "home")}
    {link("Today", "today")}
    {link("Results", "results")}
    {link("Model Health", "health")}
    {link("About", "about")}
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def hero(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
<div class="fca-hero">
  <h1>{_html(title)}</h1>
  <div class="sub">{_html(subtitle)}</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def landing_league_cards() -> None:
    leagues = [
        ("ncaab", "🏀", "NCAAB"),
        ("nba", "🏀", "NBA"),
        ("nhl", "🏒", "NHL"),
        ("mlb", "⚾", "MLB"),
        ("nfl", "🏈", "NFL"),
    ]
    st.markdown('<div class="fca-grid">', unsafe_allow_html=True)
    for sport, icon, label in leagues:
        href = f"?page=today&sport={sport}"
        st.markdown(
            f"""
<a class="league-card" href="{href}">
  <span class="league-icon">{icon}</span>
  <span>{label}</span>
</a>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


def game_card(
    sport: str,
    date: str,
    g: Dict[str, Any],
    logo_away: Optional[str] = None,
    logo_home: Optional[str] = None,
) -> None:
    teams = g.get("teams") or {}
    away = _html(teams.get("away", "Away"))
    home = _html(teams.get("home", "Home"))
    time_loc = _html(g.get("time_local") or "")
    location = _html(g.get("location") or "")

    proj = g.get("proj") or {}
    market = g.get("market") or {}

    proj_total = proj.get("proj_total")
    proj_spread = proj.get("proj_spread_home")

    def fmt(x: Any, nd: int = 1) -> str:
        try:
            if x is None:
                return "—"
            return f"{float(x):.{nd}f}"
        except Exception:
            return "—"

    spread_edge = market.get("spread_edge")
    total_edge = market.get("total_edge")

    href = f"?page=game&sport={sport}&date={date}&slug={_url_escape(g.get('slug') or '')}"

    la = f'<img src="{logo_away}" />' if logo_away else ""
    lh = f'<img src="{logo_home}" />' if logo_home else ""

    st.markdown(
        f"""
<a class="game-card" href="{href}">
  <div class="game-top">
    <div class="teamline">{la}<span>{away}</span> <span style="opacity:.75;">@</span> {lh}<span>{home}</span></div>
    <div class="meta">{time_loc}{(" • " + location) if location else ""}</div>
  </div>

  <div class="kpis">
    <div class="kpi">
      <div class="lab">Proj Total</div>
      <div class="val">{fmt(proj_total, 1)}</div>
    </div>
    <div class="kpi">
      <div class="lab">Proj Spread (Home)</div>
      <div class="val">{fmt(proj_spread, 1)}</div>
    </div>
    <div class="kpi {'missing' if spread_edge is None else ''}">
      <div class="lab">Spread Edge</div>
      <div class="val">{fmt(spread_edge, 2)}</div>
    </div>
    <div class="kpi {'missing' if total_edge is None else ''}">
      <div class="lab">Total Edge</div>
      <div class="val">{fmt(total_edge, 2)}</div>
    </div>
  </div>
</a>
        """,
        unsafe_allow_html=True,
    )


def teamrankings_bar_table(
    left_team: str,
    right_team: str,
    rows: List[Tuple[str, Optional[float], Optional[float]]],
) -> None:
    left_team = _html(strip_rank(left_team))
    right_team = _html(strip_rank(right_team))

    st.markdown('<div class="tr-table">', unsafe_allow_html=True)
    st.markdown(
        f"""
<div class="tr-row" style="padding-top:0.4rem;">
  <div class="tr-val" style="text-align:left;">{left_team}</div>
  <div class="tr-stat">STAT</div>
  <div class="tr-val" style="text-align:right;">{right_team}</div>
</div>
        """,
        unsafe_allow_html=True,
    )

    for stat, lv, rv in rows:
        stat = _html(stat)

        lv_f = _safe_float(lv)
        rv_f = _safe_float(rv)

        a = 0.0 if lv_f is None else lv_f
        b = 0.0 if rv_f is None else rv_f
        denom = abs(a) + abs(b)
        lp = 0.5 if denom == 0 else abs(a) / denom
        rp = 1.0 - lp

        if lv_f is None or rv_f is None:
            lc = "rgba(255,255,255,0.22)"
            rc = "rgba(255,255,255,0.22)"
        else:
            left_wins = lv_f >= rv_f
            lc = "rgba(20, 220, 140, 0.85)" if left_wins else "rgba(255, 80, 110, 0.85)"
            rc = "rgba(20, 220, 140, 0.85)" if not left_wins else "rgba(255, 80, 110, 0.85)"

        st.markdown(
            f"""
<div class="tr-row">
  <div>
    <div class="tr-val">{_fmt(lv_f)}</div>
    <div class="barwrap"><div class="bar" style="width:{lp*100:.0f}%; background:{lc};"></div></div>
  </div>

  <div class="tr-stat">{stat}</div>

  <div>
    <div class="tr-val" style="text-align:right;">{_fmt(rv_f)}</div>
    <div class="barwrap"><div class="bar" style="width:{rp*100:.0f}%; background:{rc}; margin-left:auto;"></div></div>
  </div>
</div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)


def render_about_page() -> None:
    st.markdown(
        """
<div class="about-shell">
  <h1 class="page-title">About <span class="accent">Edge Factor Elite</span></h1>
  <p class="page-subtitle">How our AI models work, where the data comes from, and what it all means.</p>

  <div class="about-section">
    <h2>Model Methodology</h2>
    <p>Edge Factor Elite uses two independent prediction systems that run daily before games tip off:</p>

    <div class="about-card">
      <h3 class="props-accent">Player Props Model</h3>
      <p>
        A self-learning ensemble model (Random Forest + Gradient Boosting + Extra Trees) trained on historical NBA
        player game logs. It analyzes recent performance, matchup difficulty, pace factors, rest days, and injury
        context to project player stat lines. The model compares its projections against Vegas lines to identify edges,
        and continuously adjusts its calibration based on past prediction accuracy.
      </p>
    </div>

    <div class="about-card">
      <h3 class="game-accent">Game Predictions Model</h3>
      <p>
        A team-level model that uses current season stats, advanced metrics, home/away splits, and recent form to
        project game scores. It runs Monte Carlo simulations to estimate win probabilities and compares projected
        spreads/totals against Vegas lines to find value. Picks are only recommended when the model has 55%+ confidence
        in an edge.
      </p>
    </div>
  </div>

  <div class="about-section">
    <h2>Data Sources</h2>
    <ul>
      <li>NBA API (nba.com) - player game logs, team stats, advanced metrics, daily schedules</li>
      <li>The Odds API - real-time Vegas lines (spreads, totals, moneylines) from major sportsbooks</li>
      <li>RotoWire - injury reports and player status updates</li>
    </ul>
  </div>

  <div class="about-section">
    <h2>How to Read the Projections</h2>
    <ul>
      <li><strong>Confidence %</strong> - How confident the model is in the pick. Higher is better.</li>
      <li><strong>EV% (Expected Value)</strong> - Estimated edge over the sportsbook. Positive EV means an advantage.</li>
      <li><strong>Edge Rating</strong> - STRONG (5%+), GOOD (3-5%), LEAN (1-3%) based on projected edge size.</li>
      <li><strong>NO PLAY</strong> - The model does not see enough edge to recommend a pick.</li>
    </ul>
  </div>

  <div class="about-section">
    <h2>FAQ</h2>

    <div class="faq-item">
      <div class="faq-q">When are projections updated?</div>
      <div class="faq-a">
        Projections are generated each morning. Game projections update after lines are published (usually by noon ET).
        Player props update when sportsbook prop lines are available. Results can be graded automatically throughout
        the slate.
      </div>
    </div>

    <div class="faq-item">
      <div class="faq-q">How is ROI calculated?</div>
      <div class="faq-a">
        ROI assumes standard -110 odds. Each win pays $90.91 on a $100 stake, each loss costs $100.
        ROI = total profit / total wagered * 100.
      </div>
    </div>

    <div class="faq-item">
      <div class="faq-q">Why do some days have no prop results?</div>
      <div class="faq-a">
        Player prop projections require available prop lines. If lines were missing when the model ran, no prop picks
        are generated for that day.
      </div>
    </div>

    <div class="faq-item">
      <div class="faq-q">Should I bet real money on these picks?</div>
      <div class="faq-a">
        This project is for education and entertainment only. No model guarantees profitability. Bet responsibly.
      </div>
    </div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _fmt(x: Optional[float]) -> str:
    if x is None:
        return "—"
    if abs(x) >= 10:
        return f"{x:.1f}"
    return f"{x:.3f}"


def _html(s: Any) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _url_escape(s: str) -> str:
    from urllib.parse import quote

    return quote(str(s), safe="")


def _url_unescape(s: str) -> str:
    from urllib.parse import unquote

    return unquote(s)


# ----------------- Legacy Page Compatibility -----------------

def set_selected_game(slug: str) -> None:
    st.session_state["selected_slug"] = slug
    qp = qp_get()
    qp_set(
        page="game",
        sport=str(st.session_state.get("sport") or qp.get("sport") or "ncaab"),
        date=str(qp.get("date") or ""),
        slug=str(slug or ""),
    )


def top_play_card(g: Dict[str, Any], rank: int) -> None:
    title = g.get("matchup_title") or g.get("slug") or "Matchup"
    market = g.get("market_edges") or g.get("market") or {}
    spread_edge = market.get("spread_edge")
    total_edge = market.get("total_edge")
    st.markdown(
        f"""
<div class="fca-card">
  <div class="fca-title">#{rank} {title}</div>
  <div class="fca-muted">Spread Edge: {spread_edge if spread_edge is not None else "—"} • Total Edge: {total_edge if total_edge is not None else "—"}</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def slate_row(g: Dict[str, Any]) -> None:
    title = g.get("matchup_title") or g.get("slug") or "Matchup"
    time_local = g.get("time_local") or ""
    slug = g.get("slug") or ""
    c1, c2 = st.columns([5, 1], gap="small")
    with c1:
        st.markdown(f"<div class='fca-card'><div class='fca-title'>{title}</div><div class='fca-muted'>{time_local}</div></div>", unsafe_allow_html=True)
    with c2:
        if st.button("Open", key=f"legacy_open_{slug}"):
            set_selected_game(slug)


def stat_compare_row(name: str, away_val: Any, home_val: Any, fmt: str = "{:.3f}") -> None:
    av = _safe_float(away_val)
    hv = _safe_float(home_val)
    if av is None:
        away_txt = "—"
    else:
        away_txt = fmt.format(av)
    if hv is None:
        home_txt = "—"
    else:
        home_txt = fmt.format(hv)

    st.markdown(
        f"""
<div class="tr-row">
  <div class="tr-val">{away_txt}</div>
  <div class="tr-stat">{_html(name)}</div>
  <div class="tr-val" style="text-align:right;">{home_txt}</div>
</div>
        """,
        unsafe_allow_html=True,
    )
