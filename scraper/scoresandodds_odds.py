# scraper/scoresandodds_odds.py
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.scoresandodds.com"

SPORTS = {
    # Keep MLB/NFL stubs for later if you want to expand
    "ncaab": "/ncaab",
    "nba": "/nba",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def safe_mkdir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


# ✅ NEW: scrape frequency guard (rate limiter)
def should_scrape(snapshots_dir: Path, min_interval_minutes: int) -> bool:
    """
    Return True if we should scrape now.
    Uses latest snapshot file modified time in snapshots_dir.
    """
    if min_interval_minutes <= 0:
        return True

    if not snapshots_dir.exists():
        return True

    snapshots = sorted(snapshots_dir.glob("*.json"))
    if not snapshots:
        return True

    latest = snapshots[-1]
    last_modified = datetime.fromtimestamp(latest.stat().st_mtime, tz=timezone.utc)
    delta = utc_now() - last_modified
    return delta.total_seconds() >= (min_interval_minutes * 60)


def normalize_team_name(name: str) -> str:
    """
    Normalize for joining across sources (TeamRankings vs ScoresAndOdds).
    Keep it simple and deterministic.
    """
    if not name:
        return ""
    s = name.strip().lower()
    s = s.replace("&", "and")
    s = re.sub(r"[\.\'\u2019]", "", s)  # remove periods/apostrophes
    s = re.sub(r"[^a-z0-9\s\-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def parse_american_odds(s: str) -> Optional[int]:
    if s is None:
        return None
    s = s.strip()
    if not s:
        return None
    m = re.search(r"([+-]\d+)", s)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def parse_spread_or_total_value(s: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Spread: "-1.5" or "+9.5"
    Total:  "o141.5" or "u132.5" (returns value=141.5 and side="over"/"under")
    """
    if s is None:
        return None, None
    t = s.strip().lower()
    if not t:
        return None, None

    # total style o141.5 / u132.5
    if t.startswith("o") or t.startswith("u"):
        side = "over" if t.startswith("o") else "under"
        num = re.sub(r"^[ou]\s*", "", t)
        try:
            return float(num), side
        except Exception:
            return None, side

    # spread like -1.5 / +9.5
    try:
        return float(t.replace("+", "")), None
    except Exception:
        return None, None


@dataclass
class OddsSide:
    spread: Optional[float] = None
    spread_odds: Optional[int] = None
    total: Optional[float] = None
    total_side: Optional[str] = None  # over/under
    total_odds: Optional[int] = None
    moneyline: Optional[int] = None


def fetch_html(url: str, timeout: int = 25) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/122.0.0.0 Safari/537.36"
    }
    r = requests.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.text


def build_scoreodds_url(sport: str, date_str: str) -> str:
    # ScoresAndOdds supports ?date=YYYY-MM-DD for many pages
    base_path = SPORTS.get(sport)
    if not base_path:
        raise ValueError(f"Unsupported sport: {sport}")
    return f"{BASE_URL}{base_path}?date={date_str}"


def parse_event_cards(html: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    cards = soup.select("div.event-card[id]")
    out: List[Dict[str, Any]] = []

    for card in cards:
        card_id = card.get("id", "")
        # expected like "ncaab.9133550"
        event_id = None
        if "." in card_id:
            try:
                event_id = int(card_id.split(".")[1])
            except Exception:
                event_id = None

        # each event has two rows: away + home
        rows = card.select("tr.event-card-row")
        if len(rows) < 2:
            continue

        # team names
        away_name = rows[0].select_one("span.team-name a span")
        home_name = rows[1].select_one("span.team-name a span")
        away_team = away_name.get_text(strip=True) if away_name else ""
        home_team = home_name.get_text(strip=True) if home_name else ""

        # current lines live in td with data-field
        away = OddsSide()
        home = OddsSide()

        # Spread
        away_spread_td = card.select_one('td[data-field="current-spread"][data-side="away"]')
        home_spread_td = card.select_one('td[data-field="current-spread"][data-side="home"]')
        if away_spread_td:
            v = away_spread_td.select_one("span.data-value")
            o = away_spread_td.select_one("small.data-odds")
            away.spread, _ = parse_spread_or_total_value(v.get_text(" ", strip=True) if v else "")
            away.spread_odds = parse_american_odds(o.get_text(" ", strip=True) if o else "")
        if home_spread_td:
            v = home_spread_td.select_one("span.data-value")
            o = home_spread_td.select_one("small.data-odds")
            home.spread, _ = parse_spread_or_total_value(v.get_text(" ", strip=True) if v else "")
            home.spread_odds = parse_american_odds(o.get_text(" ", strip=True) if o else "")

        # Total
        over_td = card.select_one('td[data-field="current-total"][data-side="over"]')
        under_td = card.select_one('td[data-field="current-total"][data-side="under"]')
        total_value = None
        if over_td:
            v = over_td.select_one("span.data-value")
            o = over_td.select_one("small.data-odds")
            total_value, total_side = parse_spread_or_total_value(v.get_text(" ", strip=True) if v else "")
            away.total = total_value
            away.total_side = total_side
            away.total_odds = parse_american_odds(o.get_text(" ", strip=True) if o else "")
        if under_td:
            v = under_td.select_one("span.data-value")
            o = under_td.select_one("small.data-odds")
            total_value2, total_side2 = parse_spread_or_total_value(v.get_text(" ", strip=True) if v else "")
            home.total = total_value2
            home.total_side = total_side2
            home.total_odds = parse_american_odds(o.get_text(" ", strip=True) if o else "")

        # Moneyline
        away_ml_td = card.select_one('td[data-field="current-moneyline"][data-side="away"]')
        home_ml_td = card.select_one('td[data-field="current-moneyline"][data-side="home"]')
        if away_ml_td:
            v = away_ml_td.select_one("span.data-value")
            away.moneyline = parse_american_odds(v.get_text(" ", strip=True) if v else "")
        if home_ml_td:
            v = home_ml_td.select_one("span.data-value")
            home.moneyline = parse_american_odds(v.get_text(" ", strip=True) if v else "")

        # Start time (optional)
        time_span = card.select_one('span[data-role="localtime"][data-value]')
        start_utc = time_span.get("data-value") if time_span else None

        out.append({
            "event_id": event_id,
            "source": "scoresandodds",
            "start_utc": start_utc,
            "teams": {
                "away": away_team,
                "home": home_team,
                "away_norm": normalize_team_name(away_team),
                "home_norm": normalize_team_name(home_team),
            },
            "markets": {
                "spread": {
                    "away": {"line": away.spread, "odds": away.spread_odds},
                    "home": {"line": home.spread, "odds": home.spread_odds},
                },
                "total": {
                    "line": total_value,
                    "over": {"odds": away.total_odds},
                    "under": {"odds": home.total_odds},
                },
                "moneyline": {
                    "away": away.moneyline,
                    "home": home.moneyline,
                }
            }
        })

    return out


def write_json(path: Path, data: Any) -> None:
    safe_mkdir(path.parent)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="ScoresAndOdds odds scraper (snapshot-ready).")
    ap.add_argument("--sport", default="ncaab", choices=list(SPORTS.keys()))
    ap.add_argument("--date", default=None, help="YYYY-MM-DD (default: today in UTC)")
    ap.add_argument("--data-dir", default="data", help="Base data dir")
    ap.add_argument("--timeout", type=int, default=25)

    # ✅ NEW: frequency control
    ap.add_argument(
        "--min-interval-minutes",
        type=int,
        default=15,
        help="Minimum minutes between snapshots (0 disables rate limiting)."
    )

    args = ap.parse_args()

    now = utc_now()
    date_str = args.date or now.strftime("%Y-%m-%d")

    # output dirs
    base = Path(args.data_dir) / args.sport / date_str
    snapshots_dir = base / "odds_snapshots"
    safe_mkdir(snapshots_dir)

    # ✅ NEW: skip scrape if last snapshot too recent
    if not should_scrape(snapshots_dir, args.min_interval_minutes):
        print(f"Skipping scrape — last snapshot is newer than {args.min_interval_minutes} minutes.")
        return 0

    url = build_scoreodds_url(args.sport, date_str)
    html = fetch_html(url, timeout=args.timeout)
    games = parse_event_cards(html)

    stamp = now.strftime("%H%M%S")
    snapshot_path = snapshots_dir / f"{stamp}.json"

    payload = {
        "sport": args.sport,
        "date": date_str,
        "scraped_at_utc": iso_utc(now),
        "source_url": url,
        "games": games,
    }

    write_json(snapshot_path, payload)

    # convenience pointers
    write_json(base / "latest_odds_snapshot.json", {
        "sport": args.sport,
        "date": date_str,
        "latest_snapshot": str(snapshot_path.as_posix()),
        "scraped_at_utc": iso_utc(now),
        "count": len(games),
    })

    # global latest pointer per sport (so model never picks a date)
    sport_root = Path(args.data_dir) / args.sport
    write_json(sport_root / "latest.json", {
        "sport": args.sport,
        "latest_date": date_str,
        "latest_odds_snapshot": str(snapshot_path.as_posix()),
        "scraped_at_utc": iso_utc(now),
        "count": len(games),
    })

    print(f"Saved snapshot: {snapshot_path} ({len(games)} events)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
