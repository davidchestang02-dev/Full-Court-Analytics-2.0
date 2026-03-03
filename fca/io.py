# fca/io.py
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def load_combined_daily(data_dir: str, sport: str, date_str: str) -> Dict[str, Any]:
    p = Path(data_dir) / sport / date_str / "combined_daily.json"
    if not p.exists():
        raise FileNotFoundError(f"Missing combined_daily.json: {p}")
    return read_json(p)

def load_latest_odds_snapshot(data_dir: str, sport: str) -> Dict[str, Any]:
    latest = read_json(Path(data_dir) / sport / "latest.json")
    snap_path = Path(latest["latest_odds_snapshot"])
    if not snap_path.is_absolute():
        snap_path = Path(snap_path.as_posix())  # already posix in your writer
        snap_path = Path(data_dir) / snap_path  # if you stored relative
    return read_json(snap_path)

def load_results(data_dir: str, sport: str, date_str: str) -> Optional[Dict[str, Any]]:
    p = Path(data_dir) / sport / date_str / "results" / "final_results.json"
    return read_json(p) if p.exists() else None
