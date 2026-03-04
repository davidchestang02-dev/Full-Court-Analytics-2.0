## fca/io.py
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, Optional

def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def load_combined_daily(data_dir: str, sport: str, date_str: str) -> Dict[str, Any]:
    p1 = Path(data_dir) / sport / date_str / "combined_daily.json"
    if p1.exists():
        return read_json(p1)

    # fallback: data/{sport}/latest/combined_daily.json
    p2 = Path(data_dir) / sport / "latest" / "combined_daily.json"
    if p2.exists():
        return read_json(p2)

    raise FileNotFoundError(
        f"Missing combined_daily.json. Tried:\n  {p1}\n  {p2}"
    )

def load_latest_odds_snapshot(data_dir: str, sport: str) -> Dict[str, Any]:
    latest_json = Path(data_dir) / sport / "latest.json"
    if not latest_json.exists():
        raise FileNotFoundError(f"Missing latest.json: {latest_json}")

    latest = read_json(latest_json)

    # IMPORTANT: your writer stores "data/..." already, so don't prefix data_dir again
    snap_path = Path(latest["latest_odds_snapshot"])

    # If it's relative, resolve from project root (CWD) first, then from data_dir
    if not snap_path.exists():
        snap_path2 = (Path.cwd() / snap_path).resolve()
        if snap_path2.exists():
            snap_path = snap_path2
        else:
            snap_path3 = (Path(data_dir) / snap_path).resolve()
            if snap_path3.exists():
                snap_path = snap_path3
            else:
                raise FileNotFoundError(
                    f"Odds snapshot path in latest.json not found.\n"
                    f"latest_odds_snapshot={latest['latest_odds_snapshot']}\n"
                    f"Tried:\n  {snap_path}\n  {snap_path2}\n  {snap_path3}"
                )
    return read_json(snap_path)


def load_latest_odds_snapshot_for_date(data_dir: str, sport: str, date_str: str) -> Dict[str, Any]:
    """
    Load the latest odds snapshot for a specific date folder:
      data/{sport}/{date}/latest_odds_snapshot.json -> points to odds_snapshots/*.json
    """
    latest_path = Path(data_dir) / sport / date_str / "latest_odds_snapshot.json"
    if not latest_path.exists():
        raise FileNotFoundError(f"Missing latest_odds_snapshot.json: {latest_path}")

    latest = read_json(latest_path)

    snap_ref = latest.get("latest_odds_snapshot") or latest.get("latest_snapshot")
    if not snap_ref:
        raise KeyError(f"latest_odds_snapshot.json missing snapshot pointer: {latest_path}")

    snap_path = Path(snap_ref)
    if not snap_path.is_absolute():
        snap_path = (Path.cwd() / Path(snap_path.as_posix())).resolve()
    return read_json(snap_path)


def load_odds_snapshot_for_date(data_dir: str, sport: str, date_str: str) -> Dict[str, Any]:
    # Prefer the "latest_odds_snapshot.json" pointer inside the date folder
    p = Path(data_dir) / sport / date_str / "latest_odds_snapshot.json"
    if p.exists():
        meta = read_json(p)
        snap_path = Path(meta["latest_snapshot"])
        # latest_snapshot is stored like "data/nba/2026-03-03/odds_snapshots/xxxx.json"
        if not snap_path.exists():
            snap_path = (Path.cwd() / snap_path).resolve()
        return read_json(snap_path)

    # Fallback: if no pointer, try most recent file in odds_snapshots/
    d = Path(data_dir) / sport / date_str / "odds_snapshots"
    if d.exists():
        snaps = sorted(d.glob("*.json"))
        if snaps:
            return read_json(snaps[-1])

    raise FileNotFoundError(f"No odds snapshot found for {sport} {date_str}")
    return read_json(snap_path)
