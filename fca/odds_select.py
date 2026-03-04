from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fca.io import read_json


def _parse_iso(dt: str) -> Optional[datetime]:
    if not dt:
        return None
    try:
        # handles "2026-03-03T22:24:09.032444+00:00"
        return datetime.fromisoformat(dt.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def load_odds_index(data_dir: str, sport: str, date_str: str) -> Dict[str, Any]:
    """
    Loads: data/<sport>/<date>/odds_snapshots/index.json
    """
    p = Path(data_dir) / sport / date_str / "odds_snapshots" / "index.json"
    return read_json(p)


def choose_snapshot_for_game(
    index: Dict[str, Any],
    data_dir: str,
    sport: str,
    date_str: str,
    game_start_utc: Optional[str],
) -> Optional[Dict[str, Any]]:
    """
    Pick the latest snapshot whose scraped_at_utc <= game_start_utc.
    If game_start_utc missing, fall back to last snapshot in index.
    """
    snaps: List[Dict[str, str]] = index.get("snapshots") or []
    if not snaps:
        return None

    start_dt = _parse_iso(game_start_utc) if game_start_utc else None

    # If we don't know start time, take most recent snapshot
    if not start_dt:
        last = snaps[-1]
        snap_path = Path(data_dir) / sport / date_str / last["path"]
        return read_json(snap_path)

    # Find all snapshots scraped before start
    best = None
    best_dt = None

    for s in snaps:
        sdt = _parse_iso(s.get("scraped_at_utc", ""))
        if not sdt:
            continue
        if sdt <= start_dt:
            if best_dt is None or sdt > best_dt:
                best = s
                best_dt = sdt

    # If none are before start (rare), fall back to earliest snapshot
    chosen = best or snaps[0]
    snap_path = Path(data_dir) / sport / date_str / chosen["path"]
    return read_json(snap_path)
