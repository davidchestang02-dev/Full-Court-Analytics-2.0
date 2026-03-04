from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from fca.io import read_json
from fca.join import normalize_team_name

ET = ZoneInfo("America/New_York")


def _parse_iso(dt: str) -> Optional[datetime]:
    if not dt:
        return None
    try:
        # handles "2026-03-03T22:24:09.032444+00:00"
        return datetime.fromisoformat(dt.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def load_odds_index(data_dir: str, sport: str, date_str: str) -> Dict[str, Any]:
    p = Path(data_dir) / sport / date_str / "odds_snapshots" / "index.json"
    return read_json(p)


def _match_odds_event_by_teams(game: Dict[str, Any], odds_games: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    gt = game.get("teams") or {}
    g_away = normalize_team_name(gt.get("away", ""))
    g_home = normalize_team_name(gt.get("home", ""))

    for og in odds_games:
        ot = og.get("teams") or {}
        if normalize_team_name(ot.get("away", "")) == g_away and normalize_team_name(ot.get("home", "")) == g_home:
            return og
    return None


def _load_snapshot(data_dir: str, sport: str, date_str: str, rel_path: str) -> Dict[str, Any]:
    p = Path(rel_path)
    if p.is_absolute() or p.exists():
        return read_json(p)
    return read_json(Path(data_dir) / sport / date_str / rel_path)


def _derive_start_utc_from_game(date_str: str, game: Dict[str, Any]) -> Optional[str]:
    raw = (game.get("time_local") or "").strip()
    if not raw:
        return None

    raw = raw.replace("ET", "").replace("EST", "").replace("EDT", "").strip()
    for fmt in ("%I:%M %p", "%I %p"):
        try:
            local_dt = datetime.strptime(f"{date_str} {raw}", f"%Y-%m-%d {fmt}").replace(tzinfo=ET)
            return local_dt.astimezone(timezone.utc).isoformat()
        except Exception:
            continue
    return None


def choose_pregame_odds_for_game(
    game: Dict[str, Any],
    odds_index: Dict[str, Any],
    data_dir: str,
    sport: str,
    date_str: str,
) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[int]]:
    """
    Returns:
      (odds_event_for_game, start_utc, event_id)

    - If game has no start_utc, first match the game in the latest snapshot to get start_utc + event_id.
    - Then select the last snapshot where scraped_at_utc < start_utc and return that game's odds.
    """
    snaps: List[Dict[str, str]] = odds_index.get("snapshots") or []
    if not snaps:
        return None, None, None

    latest = snaps[-1]
    latest_snap = _load_snapshot(data_dir, sport, date_str, latest["path"])
    latest_match = _match_odds_event_by_teams(game, latest_snap.get("games", []))
    if not latest_match:
        return None, None, None

    start_utc = latest_match.get("start_utc")
    event_id = latest_match.get("event_id")
    if not start_utc:
        start_utc = _derive_start_utc_from_game(date_str, game)
    start_dt = _parse_iso(start_utc)

    if not start_dt:
        return latest_match, start_utc, event_id

    best_ref: Optional[Dict[str, str]] = None
    best_dt = None

    for s in snaps:
        sdt = _parse_iso(s.get("scraped_at_utc", ""))
        if not sdt:
            continue
        if sdt < start_dt:
            if best_dt is None or sdt > best_dt:
                best_dt = sdt
                best_ref = s

    if best_ref is None:
        return None, start_utc, event_id

    best_snap = _load_snapshot(data_dir, sport, date_str, best_ref["path"])
    best_match = _match_odds_event_by_teams(game, best_snap.get("games", []))

    return best_match, start_utc, event_id
