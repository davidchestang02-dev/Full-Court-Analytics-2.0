from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def get_latest_date(data_dir: str, sport: str) -> Optional[str]:
    p = Path(data_dir) / sport / "latest.json"
    if not p.exists():
        return None
    d = read_json(p)
    return d.get("latest_date")

def load_predictions(data_dir: str, sport: str, date_str: str, model_version: str = "baseline_v1") -> Optional[Dict[str, Any]]:
    p = Path(data_dir) / sport / date_str / "predictions" / f"{model_version}.json"
    return read_json(p) if p.exists() else None

def load_combined_daily(data_dir: str, sport: str, date_str: str) -> Optional[Dict[str, Any]]:
    # supports either by-date or "latest" cache pattern
    p1 = Path(data_dir) / sport / date_str / "combined_daily.json"
    if p1.exists():
        return read_json(p1)
    p2 = Path(data_dir) / sport / "latest" / "combined_daily.json"
    return read_json(p2) if p2.exists() else None

def load_results(data_dir: str, sport: str, date_str: str) -> Optional[Dict[str, Any]]:
    p = Path(data_dir) / sport / date_str / "results" / "final_results.json"
    return read_json(p) if p.exists() else None

def list_available_dates(data_dir: str, sport: str) -> List[str]:
    sport_dir = Path(data_dir) / sport
    if not sport_dir.exists():
        return []
    dates = []
    for d in sport_dir.iterdir():
        if d.is_dir() and len(d.name) == 10 and d.name[4] == "-" and d.name[7] == "-":
            dates.append(d.name)
    return sorted(dates, reverse=True)
