# fca/join.py
from __future__ import annotations
import re
from typing import Dict, Any, List, Optional

def norm_team(s: str) -> str:
    if not s:
        return ""
    s = s.strip().lower()
    s = re.sub(r"^#\d+\s+", "", s)          # remove "#365 "
    s = s.replace("&", "and")
    s = re.sub(r"[\.\'\u2019]", "", s)
    s = re.sub(r"[^a-z0-9\s\-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def index_odds_by_teams(odds_games: List[Dict[str, Any]]) -> Dict[tuple, Dict[str, Any]]:
    idx = {}
    for g in odds_games:
        a = g["teams"].get("away_norm") or norm_team(g["teams"].get("away",""))
        h = g["teams"].get("home_norm") or norm_team(g["teams"].get("home",""))
        idx[(a, h)] = g
    return idx

def attach_odds(combined_games: List[Dict[str, Any]], odds_snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
    odds_games = odds_snapshot.get("games", [])
    idx = index_odds_by_teams(odds_games)

    out = []
    for g in combined_games:
        away = norm_team(g["teams"]["away"])
        home = norm_team(g["teams"]["home"])
        odds = idx.get((away, home))

        gg = dict(g)
        gg["odds"] = odds  # may be None
        out.append(gg)

    return out
