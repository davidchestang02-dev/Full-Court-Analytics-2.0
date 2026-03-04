# fca/io.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_combined_daily(data_dir: str, sport: str, date_str: str) -> Dict[str, Any]:
    p = Path(data_dir) / sport / date_str / "combined_daily.json"
    if not p.exists():
        raise FileNotFoundError(f"Missing combined_daily.json: {p}")
    return read_json(p)


def _resolve_snapshot_path(data_dir: str, snapshot_value: str) -> Path:
    """
    Resolve latest_odds_snapshot path stored in latest.json.

    Handles:
    1) Absolute paths (C:\\... or /...)
    2) Relative paths like 'ncaab/2026-03-03/odds_snapshots/....json'
    3) Relative paths that already include data_dir prefix like
       'data/ncaab/2026-03-03/odds_snapshots/....json' (your current writer)
    """
    data_root = Path(data_dir).resolve()
    raw = Path(snapshot_value)

    # If it's already absolute, trust it.
    if raw.is_absolute():
        return raw

    # Normalize slashes (important if stored as posix on Windows)
    raw_parts = Path(snapshot_value.replace("\\", "/")).parts

    # Case: stored as "data/..." and data_dir is also "data"
    # Avoid data/data/...
    if raw_parts and raw_parts[0].lower() == data_root.name.lower():
        raw = Path(*raw_parts[1:])  # drop leading "data"

    # Anchor to data_dir
    return (data_root / raw).resolve()


def load_latest_odds_snapshot(data_dir: str, sport: str) -> Dict[str, Any]:
    latest_path = Path(data_dir) / sport / "latest.json"
    if not latest_path.exists():
        raise FileNotFoundError(
            f"Missing latest.json for sport '{sport}': {latest_path}\n"
            f"Run the odds scraper first, e.g.\n"
            f"  python scraper/scoresandodds_odds.py --sport {sport} --data-dir {data_dir}"
        )

    latest = read_json(latest_path)

    if "latest_odds_snapshot" not in latest:
        raise KeyError(f"'latest_odds_snapshot' missing in {latest_path}")

    snap_path = _resolve_snapshot_path(data_dir, latest["latest_odds_snapshot"])

    if not snap_path.exists():
        raise FileNotFoundError(
            f"latest_odds_snapshot points to missing file:\n"
            f"  {snap_path}\n"
            f"Value in latest.json:\n"
            f"  {latest['latest_odds_snapshot']}\n"
        )

    return read_json(snap_path)


def load_results(data_dir: str, sport: str, date_str: str) -> Optional[Dict[str, Any]]:
    p = Path(data_dir) / sport / date_str / "results" / "final_results.json"
    return read_json(p) if p.exists() else None
