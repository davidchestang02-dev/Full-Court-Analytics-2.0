# fca/deterministic.py
from __future__ import annotations

from typing import Dict, Any, Optional, Tuple, List
import re
import math


def _f(x) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return None


def _get(feats: Dict[str, Any], key: str) -> Optional[float]:
    if key not in feats:
        return None
    return _f(feats.get(key))


def _detect_tokens(feats: Dict[str, Any]) -> List[str]:
    """
    Find the two team tokens from keys like:
      key_offensive_stats.off_efficiency.uk
      key_offensive_stats.off_efficiency.tam
    """
    toks = set()
    prefix = "key_offensive_stats.off_efficiency."
    for k in feats.keys():
        if k.startswith(prefix):
            toks.add(k.split(".")[-1])
    return sorted(toks)


def _map_tokens_home_away(game: Dict[str, Any], tokens: List[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Best source: tables["Matchup Menu: ..."]["team_headers"] which are like ["UK","TAM"].
    Those headers correspond to away/home in the matchup title "Away @ Home".
    Your slug example is "UK @ TAM" so headers[0]=away token, headers[1]=home token.
    """
    tables = game.get("tables", {}) or {}
    # find the matchup menu table (starts with "Matchup Menu:")
    mm = None
    for name, t in tables.items():
        if name.lower().startswith("matchup menu"):
            mm = t
            break

    if mm and isinstance(mm, dict):
        hdrs = mm.get("team_headers") or []
        # team_headers are like ["UK","TAM"] (uppercase)
        hdrs = [str(x).strip().lower() for x in hdrs if x]
        # If they match tokens directly:
        if len(hdrs) >= 2:
            away_tok, home_tok = hdrs[0], hdrs[1]
            if away_tok in tokens and home_tok in tokens:
                return home_tok, away_tok

    # Fallback: assume first token = away, second token = home (usually true but not guaranteed)
    if len(tokens) == 2:
        return tokens[1], tokens[0]

    return None, None


def _find_possessions_prefix(feats: Dict[str, Any], home_tok: str, away_tok: str) -> Optional[str]:
    """
    Finds the dynamic matchup prefix from keys like:
      kentucky_vs_texas_aandm_offensive_efficiency.possessions_gm.uk
    We just search for any key that ends with:
      "offensive_efficiency.possessions_gm.{tok}"
    and return the prefix up to ".possessions_gm"
    """
    suffix_home = f"offensive_efficiency.possessions_gm.{home_tok}"
    suffix_away = f"offensive_efficiency.possessions_gm.{away_tok}"

    for k in feats.keys():
        if k.endswith(suffix_home) or k.endswith(suffix_away):
            # remove ".possessions_gm.{tok}"
            parts = k.split(".")
            # last two parts are "possessions_gm" and token
            # so prefix is everything before that
            return ".".join(parts[:-2])  # e.g. "kentucky_vs_texas_aandm_offensive_efficiency"
    return None


def project_game(game: Dict[str, Any]) -> Dict[str, Any]:
    feats = game.get("features", {}) or {}

    tokens = _detect_tokens(feats)
    if len(tokens) != 2:
        return {"ok": False, "reason": f"token_detect_failed tokens={tokens}"}

    home_tok, away_tok = _map_tokens_home_away(game, tokens)
    if not home_tok or not away_tok:
        return {"ok": False, "reason": "home_away_token_map_failed"}

    # Core efficiencies (PPP scored / allowed)
    off_home = _get(feats, f"key_offensive_stats.off_efficiency.{home_tok}")
    off_away = _get(feats, f"key_offensive_stats.off_efficiency.{away_tok}")
    def_home = _get(feats, f"key_defensive_stats.def_efficiency.{home_tok}")
    def_away = _get(feats, f"key_defensive_stats.def_efficiency.{away_tok}")

    # Possessions from matchup-specific table (preferred)
    poss_prefix = _find_possessions_prefix(feats, home_tok, away_tok)
    poss_home = _get(feats, f"{poss_prefix}.possessions_gm.{home_tok}") if poss_prefix else None
    poss_away = _get(feats, f"{poss_prefix}.possessions_gm.{away_tok}") if poss_prefix else None

    if None in (off_home, off_away, def_home, def_away):
        return {"ok": False, "reason": "missing_core_efficiency"}

    if poss_home is None or poss_away is None:
        # If missing, fall back to a neutral default pace
        # (we’ll improve later by adding a season pace feed)
        poss = 70.0
        poss_source = "fallback_default_70"
    else:
        poss = (poss_home + poss_away) / 2.0
        poss_source = "matchup_possessions_gm"

    # PPP blend
    ppp_home = (off_home + def_away) / 2.0
    ppp_away = (off_away + def_home) / 2.0

    score_home = poss * ppp_home
    score_away = poss * ppp_away

    proj_total = score_home + score_away
    proj_spread_home = score_home - score_away

    return {
        "ok": True,
        "tokens": {"home": home_tok, "away": away_tok},
        "poss": poss,
        "poss_source": poss_source,
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

    mk = odds_game.get("markets", {}) or {}

    # --- spread parsing (robust) ---
    market_spread_home = None
    spread = mk.get("spread") or mk.get("spreads") or {}
    if isinstance(spread, dict):
        # common: spread["home"]["line"]
        if isinstance(spread.get("home"), dict) and spread["home"].get("line") is not None:
            market_spread_home = spread["home"]["line"]
        # fallback shapes (just in case)
        elif spread.get("line_home") is not None:
            market_spread_home = spread.get("line_home")
        elif spread.get("home_line") is not None:
            market_spread_home = spread.get("home_line")

    # --- total parsing (robust) ---
    market_total = None
    total = mk.get("total") or mk.get("totals") or {}
    if isinstance(total, dict):
        if total.get("line") is not None:
            market_total = total.get("line")
        elif total.get("total") is not None:
            market_total = total.get("total")

    # If neither market exists, we can't compute edges
    if market_spread_home is None and market_total is None:
        return {"has_market": False}

    out: Dict[str, Any] = {"has_market": True}

    if market_spread_home is not None:
        market_spread_home = float(market_spread_home)
        out["market_spread_home"] = market_spread_home
        out["spread_edge"] = float(proj["proj_spread_home"]) - market_spread_home

    if market_total is not None:
        market_total = float(market_total)
        out["market_total"] = market_total
        out["total_edge"] = float(proj["proj_total"]) - market_total

    return out
