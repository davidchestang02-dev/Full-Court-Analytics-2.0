from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


DATA_DIR_DEFAULT = "data"
REPO_ROOT = Path(__file__).resolve().parents[2]


def _resolve_data_dir(data_dir: str | Path = DATA_DIR_DEFAULT) -> Path:
    p = Path(data_dir)
    if p.exists():
        return p
    repo_relative = REPO_ROOT / p
    if repo_relative.exists():
        return repo_relative
    return p


def data_root() -> Path:
    return _resolve_data_dir(DATA_DIR_DEFAULT)


def _read_json(p: Path) -> Optional[Dict[str, Any]]:
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _sport_dir(data_dir: str | Path, sport: str) -> Path:
    return _resolve_data_dir(data_dir) / sport


def _day_dir(data_dir: str | Path, sport: str, date_str: str) -> Path:
    return _sport_dir(data_dir, sport) / date_str


def _is_date_folder(name: str) -> bool:
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}$", name or ""))


def strip_rank(team: str) -> str:
    if not team:
        return ""
    return re.sub(r"^\s*#\d+\s+", "", str(team)).strip()


def list_available_dates(data_dir_or_sport: str, sport: Optional[str] = None) -> List[str]:
    if sport is None:
        data_dir = DATA_DIR_DEFAULT
        sport_name = data_dir_or_sport
    else:
        data_dir = data_dir_or_sport
        sport_name = sport

    if not sport_name:
        return []

    sd = _sport_dir(data_dir, sport_name)
    if not sd.exists():
        return []

    out = sorted(
        child.name
        for child in sd.iterdir()
        if child.is_dir() and _is_date_folder(child.name)
    )

    latest = _read_json(sd / "latest.json") or {}
    latest_date = latest.get("latest_date") or latest.get("date")
    if isinstance(latest_date, str) and _is_date_folder(latest_date) and latest_date not in out:
        out.append(latest_date)

    return sorted(out)


def get_available_dates(sport: Optional[str], data_dir: str = DATA_DIR_DEFAULT) -> List[str]:
    if not sport:
        return []
    return list_available_dates(data_dir, sport)


def get_latest_date(data_dir_or_sport: str, sport: Optional[str] = None) -> Optional[str]:
    if sport is None:
        data_dir = DATA_DIR_DEFAULT
        sport_name = data_dir_or_sport
    else:
        data_dir = data_dir_or_sport
        sport_name = sport

    if not sport_name:
        return None

    sd = _sport_dir(data_dir, sport_name)
    latest = _read_json(sd / "latest.json") or {}
    latest_date = latest.get("latest_date") or latest.get("date")
    if isinstance(latest_date, str) and _is_date_folder(latest_date):
        return latest_date

    dates = list_available_dates(data_dir, sport_name)
    return dates[-1] if dates else None


def load_combined_daily(
    data_dir_or_sport: str,
    sport_or_date: str,
    date: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    if date is None:
        data_dir = DATA_DIR_DEFAULT
        sport = data_dir_or_sport
        date_str = sport_or_date
    else:
        data_dir = data_dir_or_sport
        sport = sport_or_date
        date_str = date

    if not sport or not date_str:
        return None

    p = _day_dir(data_dir, sport, date_str) / "combined_daily.json"
    data = _read_json(p)
    if data is not None:
        return data

    return _read_json(_sport_dir(data_dir, sport) / "latest" / "combined_daily.json")


def load_predictions(
    data_dir_or_sport: str,
    sport_or_date: str,
    date: Optional[str] = None,
    model_version: str = "baseline_v1",
) -> Optional[Dict[str, Any]]:
    if date is None:
        data_dir = DATA_DIR_DEFAULT
        sport = data_dir_or_sport
        date_str = sport_or_date
    else:
        data_dir = data_dir_or_sport
        sport = sport_or_date
        date_str = date

    if not sport or not date_str:
        return None

    p = _day_dir(data_dir, sport, date_str) / "predictions" / f"{model_version}.json"
    return _read_json(p)


def load_results(
    data_dir_or_sport: str,
    sport_or_date: str,
    date: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    if date is None:
        data_dir = DATA_DIR_DEFAULT
        sport = data_dir_or_sport
        date_str = sport_or_date
    else:
        data_dir = data_dir_or_sport
        sport = sport_or_date
        date_str = date

    if not sport or not date_str:
        return None

    p = _day_dir(data_dir, sport, date_str) / "results" / "final_results.json"
    return _read_json(p)


def merge_slate_with_preds(
    combined: Dict[str, Any],
    preds: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    games = combined.get("games") or combined.get("matchups") or []
    pred_map: Dict[str, Dict[str, Any]] = {}
    if preds:
        for x in preds.get("predictions", []):
            slug = x.get("slug")
            if slug:
                pred_map[slug] = x

    out: List[Dict[str, Any]] = []
    for g in games:
        slug = g.get("slug")
        px = pred_map.get(slug, {})
        teams = g.get("teams") or {}
        away = teams.get("away", "")
        home = teams.get("home", "")
        out.append(
            {
                "slug": slug,
                "matchup_title": g.get("matchup_title"),
                "time_local": g.get("time_local"),
                "location": g.get("location"),
                "teams": {
                    "away_raw": away,
                    "home_raw": home,
                    "away": strip_rank(away),
                    "home": strip_rank(home),
                    "neutral_site": bool(teams.get("neutral_site", False)),
                },
                "features": g.get("features") or {},
                "tables": g.get("tables") or {},
                "proj": px.get("proj") or {},
                "market": px.get("market") or px.get("market_edges") or {},
                "odds_event_id": px.get("odds_event_id"),
            }
        )
    return out


@dataclass
class GamesBundle:
    sport: str
    date: str
    source: str  # combined_daily | schedule_only | latest_combined | latest_schedule | empty
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

    preds = load_predictions(data_dir, sport, date_str, model_version="baseline_v1")
    results = load_results(data_dir, sport, date_str)

    if combined and (combined.get("games") or combined.get("matchups")):
        games = combined.get("games") or combined.get("matchups") or []
        return GamesBundle(sport=sport, date=date_str, source="combined_daily", games=games, predictions=preds, results=results)

    if schedule and (schedule.get("games") or schedule.get("matchups")):
        games = schedule.get("games") or schedule.get("matchups") or []
        return GamesBundle(sport=sport, date=date_str, source="schedule_only", games=games, predictions=preds, results=results)

    # Fallback to latest cache files so Streamlit Cloud can still show today's slate
    # when dated folders are not fully present in the repo.
    latest_dir = _sport_dir(data_dir, sport) / "latest"
    latest_combined = _read_json(latest_dir / "combined_daily.json")
    latest_schedule = _read_json(latest_dir / "schedule.json")

    if latest_combined and (latest_combined.get("games") or latest_combined.get("matchups")):
        games = latest_combined.get("games") or latest_combined.get("matchups") or []
        return GamesBundle(sport=sport, date=date_str, source="latest_combined", games=games, predictions=preds, results=results)

    if latest_schedule and (latest_schedule.get("games") or latest_schedule.get("matchups")):
        games = latest_schedule.get("games") or latest_schedule.get("matchups") or []
        return GamesBundle(sport=sport, date=date_str, source="latest_schedule", games=games, predictions=preds, results=results)

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
