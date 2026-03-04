from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _read_json(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def list_available_sports(data_dir: str = "data") -> List[str]:
    root = Path(data_dir)
    if not root.exists():
        return []
    return sorted([p.name for p in root.iterdir() if p.is_dir()])


def get_default_sport(sports: List[str]) -> str:
    # Prefer ncaab if present
    for s in ("ncaab", "nba"):
        if s in sports:
            return s
    return sports[0] if sports else "ncaab"


def get_default_date(data_dir: str, sport: str) -> str:
    latest = Path(data_dir) / sport / "latest.json"
    if latest.exists():
        try:
            j = _read_json(latest)
            return j.get("latest_date") or j.get("date") or ""
        except Exception:
            pass
    # fallback: most recent folder
    sport_dir = Path(data_dir) / sport
    if sport_dir.exists():
        dates = sorted([p.name for p in sport_dir.iterdir() if p.is_dir() and p.name[:4].isdigit()])
        return dates[-1] if dates else ""
    return ""


def load_predictions(data_dir: str, sport: str, date: str, model_version: str = "baseline_v1") -> Optional[Dict[str, Any]]:
    p = Path(data_dir) / sport / date / "predictions" / f"{model_version}.json"
    return _read_json(p) if p.exists() else None


def load_combined_daily(data_dir: str, sport: str, date: str) -> Optional[Dict[str, Any]]:
    p = Path(data_dir) / sport / date / "combined_daily.json"
    # some pipelines copy to data/{sport}/latest/combined_daily.json
    if not p.exists():
        p = Path(data_dir) / sport / "latest" / "combined_daily.json"
    return _read_json(p) if p.exists() else None


def load_results(data_dir: str, sport: str, date: str) -> Optional[Dict[str, Any]]:
    p = Path(data_dir) / sport / date / "results" / "final_results.json"
    return _read_json(p) if p.exists() else None


def list_dates(data_dir: str, sport: str) -> List[str]:
    sport_dir = Path(data_dir) / sport
    if not sport_dir.exists():
        return []
    dates = []
    for p in sport_dir.iterdir():
        if p.is_dir() and len(p.name) == 10 and p.name[4] == "-" and p.name[7] == "-":
            dates.append(p.name)
    return sorted(dates)
