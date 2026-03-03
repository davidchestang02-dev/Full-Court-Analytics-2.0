# model_pipeline.py
from __future__ import annotations
import argparse
import json
from pathlib import Path
from datetime import datetime, timezone

from fca.io import load_combined_daily, load_latest_odds_snapshot
from fca.join import attach_odds
from fca.deterministic import project_game, market_edges

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sport", default="ncaab")
    ap.add_argument("--date", required=True)     # keep explicit for now
    ap.add_argument("--data-dir", default="data")
    args = ap.parse_args()

    combined = load_combined_daily(args.data_dir, args.sport, args.date)
    odds = load_latest_odds_snapshot(args.data_dir, args.sport)

    games = combined.get("games") or combined.get("matchups") or []
    games_joined = attach_odds(games, odds)

    preds = []
    for g in games_joined:
        proj = project_game(g)
        edges = market_edges(proj, g.get("odds"))
        preds.append({
            "slug": g.get("slug"),
            "matchup_title": g.get("matchup_title"),
            "teams": g.get("teams"),
            "time_local": g.get("time_local"),
            "proj": proj,
            "market": edges,
            "odds_event_id": (g["odds"]["event_id"] if g.get("odds") else None),
        })

    out = {
        "sport": args.sport,
        "date": args.date,
        "built_at_utc": utc_now_iso(),
        "model_version": "baseline_v1",
        "count": len(preds),
        "predictions": preds,
    }

    out_path = Path(args.data_dir) / args.sport / args.date / "predictions" / "baseline_v1.json"
    write_json(out_path, out)

    print(f"Saved predictions: {out_path} ({len(preds)} games)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
