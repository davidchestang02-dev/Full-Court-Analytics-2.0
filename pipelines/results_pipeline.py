from __future__ import annotations

import argparse
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
import sys

# Ensure `fca` is importable when running as: python pipelines/results_pipeline.py
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# reuse your normalizer so joins are consistent
from fca.join import norm_team
from fca.io import read_json


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _safe_float(x) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _safe_int(x) -> Optional[int]:
    try:
        if x is None:
            return None
        return int(x)
    except Exception:
        return None


def _pick_latest_board_snapshot(data_dir: str, sport: str, date_str: str) -> Path:
    """
    We prefer the board snapshot "latest_odds_snapshot.json" if it exists,
    otherwise we look for odds_snapshots/index.json and pick the last entry,
    otherwise we fall back to any *.json in odds_snapshots/ excluding index.json.
    """
    base = Path(data_dir) / sport / date_str / "odds_snapshots"

    latest_pointer = Path(data_dir) / sport / date_str / "latest_odds_snapshot.json"
    if latest_pointer.exists():
        ptr = json.loads(latest_pointer.read_text(encoding="utf-8"))
        p = Path(ptr.get("latest_odds_snapshot") or ptr.get("latest_snapshot") or "")
        if not p.is_absolute():
            p = (Path.cwd() / p).resolve()
        if p.exists() and p.is_file():
            return p

    idx = base / "index.json"
    if idx.exists():
        d = json.loads(idx.read_text(encoding="utf-8"))
        snaps = d.get("snapshots") or []
        if snaps:
            last = snaps[-1]
            p = Path(last["path"])
            if not p.is_absolute():
                p = (Path.cwd() / p).resolve()
            if p.exists():
                return p

    if base.exists():
        candidates = sorted([p for p in base.glob("*.json") if p.name != "index.json"])
        if candidates:
            return candidates[-1]

    raise FileNotFoundError(f"No board odds snapshot found in: {base}")


def _build_board_indexes(board: Dict[str, Any]):
    by_event_id: Dict[int, Dict[str, Any]] = {}
    by_teams: Dict[Tuple[str, str], Dict[str, Any]] = {}

    for g in board.get("games", []) or []:
        eid = _safe_int(g.get("event_id"))
        if eid is not None:
            by_event_id[eid] = g

        t = g.get("teams") or {}
        a = norm_team(t.get("away", ""))
        h = norm_team(t.get("home", ""))
        if a and h:
            by_teams[(a, h)] = g

    return by_event_id, by_teams


def grade_su(final_away: Optional[int], final_home: Optional[int]) -> Dict[str, Any]:
    if final_away is None or final_home is None:
        return {"graded": False}

    if final_home > final_away:
        winner = "home"
    elif final_away > final_home:
        winner = "away"
    else:
        winner = "push"

    return {
        "graded": True,
        "winner": winner,
        "final_away": final_away,
        "final_home": final_home,
        "final_total": final_away + final_home,
        "final_margin_home": final_home - final_away,
    }


def grade_ats(final_away: Optional[int], final_home: Optional[int], close_spread_home: Optional[float]) -> Dict[str, Any]:
    if final_away is None or final_home is None or close_spread_home is None:
        return {"graded": False}

    margin_home = (final_home - final_away)
    # Home covers if margin_home + home_line > 0
    v = margin_home + close_spread_home

    if v > 0:
        winner = "home"
    elif v < 0:
        winner = "away"
    else:
        winner = "push"

    return {
        "graded": True,
        "close_spread_home": close_spread_home,
        "ats_winner": winner,
        "cover_margin": v,  # >0 home cover, <0 away cover, 0 push
    }


def grade_ou(final_total: Optional[int], close_total: Optional[float]) -> Dict[str, Any]:
    if final_total is None or close_total is None:
        return {"graded": False}

    diff = final_total - close_total
    if diff > 0:
        result = "over"
    elif diff < 0:
        result = "under"
    else:
        result = "push"

    return {
        "graded": True,
        "close_total": close_total,
        "ou_result": result,
        "ou_diff": diff,  # >0 over, <0 under, 0 push
    }


def extract_closing_markets(board_game: Dict[str, Any]) -> Dict[str, Any]:
    mk = board_game.get("markets") or {}
    spread = mk.get("spread") or {}
    total = mk.get("total") or {}
    ml = mk.get("moneyline") or {}

    close_spread_home = _safe_float(((spread.get("home") or {}).get("line")))
    close_spread_away = _safe_float(((spread.get("away") or {}).get("line")))
    close_total = _safe_float(total.get("line"))

    return {
        "spread": {
            "home": {"line": close_spread_home, "odds": (spread.get("home") or {}).get("odds")},
            "away": {"line": close_spread_away, "odds": (spread.get("away") or {}).get("odds")},
        },
        "total": {
            "line": close_total,
            "over_odds": (total.get("over") or {}).get("odds"),
            "under_odds": (total.get("under") or {}).get("odds"),
        },
        "moneyline": {
            "home": {"odds": (ml.get("home") or {}).get("odds")},
            "away": {"odds": (ml.get("away") or {}).get("odds")},
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sport", required=True, choices=["ncaab", "nba"])
    ap.add_argument("--date", required=True)  # YYYY-MM-DD
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--model-version", default="baseline_v1")
    args = ap.parse_args()

    pred_path = Path(args.data_dir) / args.sport / args.date / "predictions" / f"{args.model_version}.json"
    if not pred_path.exists():
        raise FileNotFoundError(f"Missing predictions file: {pred_path}")

    preds_doc = read_json(pred_path)
    preds = preds_doc.get("predictions") or []

    board_path = _pick_latest_board_snapshot(args.data_dir, args.sport, args.date)
    board_doc = read_json(board_path)

    by_event_id, by_teams = _build_board_indexes(board_doc)

    out_games = []
    join_stats = {"joined_by_event_id": 0, "joined_by_teams": 0, "missing_board_game": 0}

    graded_stats = {"su_graded": 0, "ats_graded": 0, "ou_graded": 0}

    for p in preds:
        odds_event_id = _safe_int(p.get("odds_event_id"))
        teams = p.get("teams") or {}
        away_name = teams.get("away")
        home_name = teams.get("home")

        board_game = None
        join_method = None

        if odds_event_id is not None and odds_event_id in by_event_id:
            board_game = by_event_id[odds_event_id]
            join_method = "event_id"
            join_stats["joined_by_event_id"] += 1
        else:
            key = (norm_team(away_name or ""), norm_team(home_name or ""))
            if key in by_teams:
                board_game = by_teams[key]
                join_method = "teams"
                join_stats["joined_by_teams"] += 1

        if not board_game:
            join_stats["missing_board_game"] += 1
            out_games.append({
                "slug": p.get("slug"),
                "matchup_title": p.get("matchup_title"),
                "teams": teams,
                "odds_event_id": odds_event_id,
                "join": {"ok": False, "method": None},
                "result": {"ok": False, "reason": "board_game_not_found"},
            })
            continue

        final = board_game.get("final") or {}
        final_away = _safe_int(final.get("away"))
        final_home = _safe_int(final.get("home"))

        markets = extract_closing_markets(board_game)
        close_spread_home = markets["spread"]["home"]["line"]
        close_total = markets["total"]["line"]

        su = grade_su(final_away, final_home)
        ats = grade_ats(final_away, final_home, close_spread_home)
        ou = grade_ou((su.get("final_total") if su.get("graded") else None), close_total)

        if su.get("graded"):
            graded_stats["su_graded"] += 1
        if ats.get("graded"):
            graded_stats["ats_graded"] += 1
        if ou.get("graded"):
            graded_stats["ou_graded"] += 1

        out_games.append({
            "slug": p.get("slug"),
            "matchup_title": p.get("matchup_title"),
            "teams": teams,
            "time_local": p.get("time_local"),
            "odds_event_id": odds_event_id,
            "board": {
                "event_id": _safe_int(board_game.get("event_id")),
                "state": board_game.get("state"),
                "start_utc": board_game.get("start_utc"),
                "snapshot_path": str(board_path).replace("\\", "/"),
            },
            "join": {"ok": True, "method": join_method},
            "closing": markets,
            "final": {"away": final_away, "home": final_home},
            "grading": {
                "su": su,
                "ats": ats,
                "ou": ou,
            },
            # include your model output for the app
            "proj": p.get("proj"),
            "market_edges": p.get("market"),
        })

    out = {
        "sport": args.sport,
        "date": args.date,
        "built_at_utc": utc_now_iso(),
        "model_version": args.model_version,
        "inputs": {
            "predictions_path": str(pred_path).replace("\\", "/"),
            "board_snapshot_path": str(board_path).replace("\\", "/"),
        },
        "counts": {
            "predictions": len(preds),
            "results": len(out_games),
        },
        "join_stats": join_stats,
        "graded_stats": graded_stats,
        "games": out_games,
    }

    out_path = Path(args.data_dir) / args.sport / args.date / "results" / "final_results.json"
    write_json(out_path, out)
    print(f"Saved results: {out_path} (SU graded: {graded_stats['su_graded']}, ATS graded: {graded_stats['ats_graded']}, OU graded: {graded_stats['ou_graded']})")
    print(f"Join stats: {join_stats}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
