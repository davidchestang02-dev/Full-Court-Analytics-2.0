# fca/join.py
from __future__ import annotations
import re
from typing import Dict, Any, List, Optional

def normalize_team_name(name: str) -> str:
    if not name:
        return ""
    s = name.strip().lower()
    s = re.sub(r"^#\d+\s+", "", s)          # remove leading ranks like "#12 "
    s = s.replace("&", "and")
    s = re.sub(r"[\.\'\u2019]", "", s)
    s = re.sub(r"[^a-z0-9\s\-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def norm_team(s: str) -> str:
    if not s:
        return ""
    s = s.strip().lower()

    # remove leading rank tokens:
    # "#365 miss valley st" -> "miss valley st"
    # "# 365 miss valley st" -> "miss valley st"
    # "365 miss valley st" -> "miss valley st"
    s = re.sub(r"^\s*#\s*\d+\s+", "", s)
    s = re.sub(r"^\s*\d+\s+", "", s)

    s = s.replace("&", "and")
    s = re.sub(r"[\.\'\u2019]", "", s)
    s = re.sub(r"[^a-z0-9\s\-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def index_odds_by_teams(odds_games: List[Dict[str, Any]]) -> Dict[tuple, Dict[str, Any]]:
    idx = {}
    for g in odds_games:
        a = g["teams"].get("away_norm") or normalize_team_name(g["teams"].get("away", ""))
        h = g["teams"].get("home_norm") or normalize_team_name(g["teams"].get("home", ""))
        idx[(a, h)] = g
    return idx

def attach_odds(combined_games: List[Dict[str, Any]], odds_snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
    odds_games = odds_snapshot.get("games", [])
    idx = index_odds_by_teams(odds_games)

    out = []
    for g in combined_games:
        away = normalize_team_name(g["teams"]["away"])
        home = normalize_team_name(g["teams"]["home"])
        odds = idx.get((away, home))

        gg = dict(g)
        gg["odds"] = odds  # may be None
        out.append(gg)

    return out
