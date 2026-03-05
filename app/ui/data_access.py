from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


DATA_DIR_DEFAULT = "data"


def _read_json(p: Path) -> Optional[Dict[str, Any]]:
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _sport_dir(data_dir: str, sport: str) -> Path:
    return Path(data_dir) / sport


def _day_dir(data_dir: str, sport: str, date_str: str) -> Path:
    return Path(data_dir) / sport / date_str


def get_available_dates(sport: Optional[str], data_dir: str = DATA_DIR_DEFAULT) -> List[str]:
    if not sport:
        return []
    sd = _sport_dir(data_dir, sport)
    if not sd.exists():
        return []
    out = []
    for child in sd.iterdir():
        if child.is_dir():
            # date folders only
            name = child.name
            if len(name) == 10 and name[4] == "-" and name[7] == "-":
                out.append(name)
    return sorted(out)


@dataclass
class GamesBundle:
    sport: str
    date: str
    source: str  # combined_daily | schedule_only | empty
    games: List[Dict[str, Any]]
    predictions: Optional[Dict[str, Any]] = None
    results: Optional[Dict[str, Any]] = None


def load_games_for_date(sport: str, date_str: str, data_dir: str = DATA_DIR_DEFAULT) -> GamesBundle:
    """
    Priority:
      1) combined_daily.json (has matchups + TR features)
      2) schedule.json (fallback so UI still shows slate)
      3) empty
    Plus:
      - predictions/baseline_v1.json if exists
      - results/final_results.json if exists
    """
    dd = _day_dir(data_dir, sport, date_str)

    combined = _read_json(dd / "combined_daily.json")
    schedule = _read_json(dd / "schedule.json")

    preds = _read_json(dd / "predictions" / "baseline_v1.json")
    results = _read_json(dd / "results" / "final_results.json")

    if combined and (combined.get("games") or combined.get("matchups")):
        games = combined.get("games") or combined.get("matchups") or []
        return GamesBundle(sport=sport, date=date_str, source="combined_daily", games=games, predictions=preds, results=results)

    if schedule and (schedule.get("games") or schedule.get("matchups")):
        games = schedule.get("games") or schedule.get("matchups") or []
        return GamesBundle(sport=sport, date=date_str, source="schedule_only", games=games, predictions=preds, results=results)

    return GamesBundle(sport=sport, date=date_str, source="empty", games=[], predictions=preds, results=results)


def _index_predictions(preds: Dict[str, Any] | None) -> Dict[str, Dict[str, Any]]:
    if not preds:
        return {}
    arr = preds.get("predictions") or []
    idx = {}
    for p in arr:
        slug = p.get("slug")
        if slug:
            idx[slug] = p
    return idx


def _index_results(res: Dict[str, Any] | None) -> Dict[str, Dict[str, Any]]:
    if not res:
        return {}
    arr = res.get("games") or res.get("results") or res.get("finals") or []
    idx = {}
    for g in arr:
        slug = g.get("slug")
        if slug:
            idx[slug] = g
    return idx


def load_game_detail_bundle(sport: str, date_str: str, slug: str, data_dir: str = DATA_DIR_DEFAULT) -> Dict[str, Any]:
    """
    Returns a unified object:
      - base matchup (from combined_daily or schedule)
      - prediction row (if exists)
      - result row (if exists)
    """
    bundle = load_games_for_date(sport, date_str, data_dir=data_dir)
    pred_idx = _index_predictions(bundle.predictions)
    res_idx = _index_results(bundle.results)

    base = next((g for g in bundle.games if g.get("slug") == slug), None)

    return {
        "sport": sport,
        "date": date_str,
        "slug": slug,
        "bundle_source": bundle.source,
        "base": base,
        "prediction": pred_idx.get(slug),
        "result": res_idx.get(slug),
    }
