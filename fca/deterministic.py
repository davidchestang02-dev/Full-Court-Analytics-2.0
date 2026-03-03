# fca/deterministic.py
from __future__ import annotations
from typing import Dict, Any, Optional
import math

def _get(feats: Dict[str, Any], key: str) -> Optional[float]:
    v = feats.get(key)
    if v is None:
        return None
    try:
        return float(v)
    except:
        return None

def project_game(game: Dict[str, Any]) -> Dict[str, Any]:
    feats = game.get("features", {})

    # pick the matchup-specific keys (you have both key_offensive_stats + matchup tables)
    # We'll use the long "miss_valley_st_vs_alcorn_st_*" keys when present, fallback to key_*.
    # We can detect mvsu/alcn tokens from the keys if needed later. For now: use key_*.
    off_home = _get(feats, "key_offensive_stats.off_efficiency.alcn")  # example
    off_away = _get(feats, "key_offensive_stats.off_efficiency.mvsu")
    def_home = _get(feats, "key_defensive_stats.def_efficiency.alcn")
    def_away = _get(feats, "key_defensive_stats.def_efficiency.mvsu")

    poss_home = _get(feats, "miss_valley_st_vs_alcorn_st_offensive_efficiency.possessions_gm.alcn")
    poss_away = _get(feats, "miss_valley_st_vs_alcorn_st_offensive_efficiency.possessions_gm.mvsu")

    # If these exact keys don't exist for other games, we’ll switch to a dynamic key finder later.
    # For now, we guard:
    if poss_home is None or poss_away is None:
        poss_home = _get(feats, "key_offensive_stats.possessions_gm.home")  # placeholder for later
        poss_away = _get(feats, "key_offensive_stats.possessions_gm.away")

    poss = None
    if poss_home is not None and poss_away is not None:
        poss = (poss_home + poss_away) / 2.0

    # PPP blend (offense vs opponent defense)
    # def_eff is PPP allowed; off_eff is PPP scored
    if None in (off_home, off_away, def_home, def_away, poss):
        return {"ok": False, "reason": "missing_core_features"}

    ppp_home = (off_home + def_away) / 2.0
    ppp_away = (off_away + def_home) / 2.0

    score_home = poss * ppp_home
    score_away = poss * ppp_away

    proj_total = score_home + score_away
    proj_spread_home = score_home - score_away

    return {
        "ok": True,
        "poss": poss,
        "ppp_home": ppp_home,
        "ppp_away": ppp_away,
        "proj_home": score_home,
        "proj_away": score_away,
        "proj_total": proj_total,
        "proj_spread_home": proj_spread_home,
    }

def market_edges(proj: Dict[str, Any], odds_game: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not proj.get("ok") or not odds_game:
        return {"has_market": False}

    mk = odds_game.get("markets", {})
    spread = mk.get("spread", {})
    total = mk.get("total", {})

    # ScoresAndOdds spread lines: away line and home line
    market_spread_home = spread.get("home", {}).get("line")  # e.g. -9.5
    market_total = total.get("line")

    if market_spread_home is None or market_total is None:
        return {"has_market": False}

    spread_edge = proj["proj_spread_home"] - float(market_spread_home)
    total_edge = proj["proj_total"] - float(market_total)

    return {
        "has_market": True,
        "market_spread_home": float(market_spread_home),
        "market_total": float(market_total),
        "spread_edge": spread_edge,
        "total_edge": total_edge,
    }
