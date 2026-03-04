from __future__ import annotations

import argparse
import json
from pathlib import Path
from datetime import datetime, timezone
import re
import requests
from bs4 import BeautifulSoup

SPORT_PATH = {
    "ncaab": "ncaab",
    "nba": "nba",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_float(x):
    try:
        return float(x)
    except Exception:
        return None


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _parse_line_text(txt: str):
    """
    Examples:
      "-1.5"
      "o137.5"
      "u227.5"
    """
    t = (txt or "").strip().lower()
    if not t:
        return None, None
    if t.startswith("o"):
        return "over", safe_float(t[1:])
    if t.startswith("u"):
        return "under", safe_float(t[1:])
    return "spread", safe_float(t)


def _parse_odds_text(txt: str):
    """
    Examples: "-105", "+120", "even"
    """
    t = (txt or "").strip().lower()
    if not t:
        return None
    if t == "even":
        return 100
    # strip non +-digits
    t = re.sub(r"[^0-9\-\+]", "", t)
    try:
        return int(t)
    except Exception:
        return None


def fetch_board_html(sport: str, date_str: str) -> str:
    # ScoresAndOdds board pages are typically like:
    # https://www.scoresandodds.com/ncaab?date=YYYY-MM-DD
    # https://www.scoresandodds.com/nba?date=YYYY-MM-DD
    base = "https://www.scoresandodds.com"
    url = f"{base}/{SPORT_PATH[sport]}?date={date_str}"
    r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return r.text


def parse_board(html: str, sport: str) -> dict:
    soup = BeautifulSoup(html, "lxml")

    games = []
    # event cards look like: <div id="ncaab.8582790" class="event-card" ...>
    for card in soup.select("div.event-card[id*='.']"):
        cid = card.get("id", "")
        # id is like "ncaab.8582790" or "nba.10569530"
        try:
            card_sport, event_id_str = cid.split(".", 1)
            event_id = int(event_id_str)
        except Exception:
            continue

        if card_sport != sport:
            # page can include ads/other; keep only correct sport
            continue

        # state + localtime start_utc are in the header row
        header = card.select_one("tr.event-card-header")
        state = None
        start_utc = None
        if header:
            st = header.select_one("[data-field='state']")
            if st:
                state = st.get_text(strip=True) or None
            lt = header.select_one("[data-role='localtime'][data-value]")
            if lt:
                start_utc = lt.get("data-value")

        rows = card.select("tr.event-card-row")
        if len(rows) < 2:
            continue

        def parse_side(row):
            # team name
            team_a = row.select_one(".team-name a span")
            team = team_a.get_text(strip=True) if team_a else None

            # score (if final/live)
            score_td = row.select_one("td.event-card-score")
            score = safe_float(score_td.get_text(strip=True)) if score_td else None

            # spread cell
            spread_td = row.select_one("[data-field='live-spread']")
            spread_line = None
            spread_odds = None
            if spread_td:
                line_span = spread_td.select_one(".data-value")
                odds_small = spread_td.select_one(".data-odds")
                kind, val = _parse_line_text(line_span.get_text(strip=True) if line_span else "")
                # kind should be "spread"
                spread_line = val
                spread_odds = _parse_odds_text(odds_small.get_text(strip=True) if odds_small else "")

            # total cell (over row contains oXXX, under row contains uXXX)
            total_td = row.select_one("[data-field='live-total']")
            total_line = None
            total_side = None
            total_odds = None
            if total_td:
                line_span = total_td.select_one(".data-value")
                odds_small = total_td.select_one(".data-odds")
                kind, val = _parse_line_text(line_span.get_text(strip=True) if line_span else "")
                # kind is "over"/"under"
                total_side = kind
                total_line = val
                total_odds = _parse_odds_text(odds_small.get_text(strip=True) if odds_small else "")

            # moneyline
            ml_td = row.select_one("[data-field='live-moneyline']")
            ml = None
            if ml_td:
                ml_span = ml_td.select_one(".data-value")
                ml = _parse_odds_text(ml_span.get_text(strip=True) if ml_span else "")

            # css classes can tell cover results in FINAL cards
            spread_class = (spread_td.get("class") if spread_td else []) or []
            total_class = (total_td.get("class") if total_td else []) or []
            ml_class = (ml_td.get("class") if ml_td else []) or []
            return {
                "team": team,
                "score": int(score) if score is not None else None,
                "spread": {"line": spread_line, "odds": spread_odds, "classes": spread_class},
                "total": {"side": total_side, "line": total_line, "odds": total_odds, "classes": total_class},
                "moneyline": {"odds": ml, "classes": ml_class},
            }

        away = parse_side(rows[0])
        home = parse_side(rows[1])

        # normalize totals into one market object
        # We want: total.line plus over/under odds
        total_line = away["total"]["line"] or home["total"]["line"]
        over_odds = away["total"]["odds"] if away["total"]["side"] == "over" else home["total"]["odds"]
        under_odds = away["total"]["odds"] if away["total"]["side"] == "under" else home["total"]["odds"]

        games.append({
            "event_id": event_id,
            "state": state,
            "start_utc": start_utc,
            "teams": {"away": away["team"], "home": home["team"]},
            "final": {"away": away["score"], "home": home["score"]},
            "markets": {
                "spread": {
                    "away": {"line": away["spread"]["line"], "odds": away["spread"]["odds"]},
                    "home": {"line": home["spread"]["line"], "odds": home["spread"]["odds"]},
                },
                "total": {
                    "line": total_line,
                    "over": {"odds": over_odds},
                    "under": {"odds": under_odds},
                },
                "moneyline": {
                    "away": {"odds": away["moneyline"]["odds"]},
                    "home": {"odds": home["moneyline"]["odds"]},
                }
            },
            # keep raw CSS result signals (optional but useful)
            "signals": {
                "spread": {"away": away["spread"]["classes"], "home": home["spread"]["classes"]},
                "total": {"away": away["total"]["classes"], "home": home["total"]["classes"]},
                "moneyline": {"away": away["moneyline"]["classes"], "home": home["moneyline"]["classes"]},
            }
        })

    return {
        "sport": sport,
        "scraped_at_utc": utc_now_iso(),
        "games": games,
    }


def update_index(index_path: Path, snapshot_rel: str, scraped_at_utc: str, count: int) -> None:
    idx = {"snapshots": []}
    if index_path.exists():
        idx = json.loads(index_path.read_text(encoding="utf-8"))

    idx["snapshots"].append({
        "path": snapshot_rel.replace("\\", "/"),
        "scraped_at_utc": scraped_at_utc,
        "count": count
    })
    # keep sorted
    idx["snapshots"].sort(key=lambda x: x["scraped_at_utc"])
    write_json(index_path, idx)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sport", required=True, choices=["ncaab", "nba"])
    ap.add_argument("--date", required=True)  # YYYY-MM-DD
    ap.add_argument("--data-dir", default="data")
    args = ap.parse_args()

    html = fetch_board_html(args.sport, args.date)
    snap = parse_board(html, args.sport)

    # save snapshot
    out_dir = Path(args.data_dir) / args.sport / args.date / "odds_snapshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%H%M%S")
    snap_path = out_dir / f"{stamp}.json"
    write_json(snap_path, snap)

    # update index manifest
    index_path = out_dir / "index.json"
    snap_rel = str(snap_path).replace("\\", "/")
    update_index(index_path, snap_rel, snap["scraped_at_utc"], len(snap["games"]))

    # update latest.json
    dated_latest_path = Path(args.data_dir) / args.sport / args.date / "latest_odds_snapshot.json"
    dated_latest = {
        "sport": args.sport,
        "date": args.date,
        "latest_odds_snapshot": snap_rel,
        "latest_snapshot": snap_rel,
        "scraped_at_utc": snap["scraped_at_utc"],
        "count": len(snap["games"]),
    }
    write_json(dated_latest_path, dated_latest)

    latest_path = Path(args.data_dir) / args.sport / "latest.json"
    latest = {
        "sport": args.sport,
        "latest_date": args.date,
        "latest_odds_snapshot": snap_rel,
        "scraped_at_utc": snap["scraped_at_utc"],
        "count": len(snap["games"]),
    }
    write_json(latest_path, latest)

    print(f"Saved board snapshot: {snap_path} ({len(snap['games'])} events)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
