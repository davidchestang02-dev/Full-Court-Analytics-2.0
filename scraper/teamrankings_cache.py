#!/usr/bin/env python3
"""
TeamRankings Daily Cache Engine (Model-Friendly)
------------------------------------------------

Outputs:
data/
  index.json
  nba/
    latest_date.json
    latest/schedule.json
    latest/combined_daily.json
    YYYY-MM-DD/
      schedule.json
      combined_daily.json
      matchups/<slug>.json
  ncaab/
    ...

Features:
- Season-aware (out-of-season => pointers update cleanly)
- Normalized teams: {home, away, neutral_site}
- Numeric parsing: percents -> 0..1 float, numbers -> float, +/-, commas handled
- Clean ML schema:
    - tables: structured
    - features: flat key->float map for easy ingestion
- Atomic JSON writes
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE = "https://www.teamrankings.com"

SPORTS = {
    "nba": {
        "schedule_url": f"{BASE}/nba/schedules/",
        "matchup_suffix": "/efficiency",
    },
    "ncaab": {
        "schedule_url": f"{BASE}/ncb/schedules/",
        "matchup_suffix": "/efficiency",
    },
    # Ready when in season
    "mlb": {
        "schedule_url": f"{BASE}/mlb/schedules/",
        "matchup_suffix": "/stats",
    },
    "nfl": {
        "schedule_url": f"{BASE}/nfl/schedules/",
        "matchup_suffix": "/stats",
    },
    "ncaaf": {
        "schedule_url": f"{BASE}/college-football/schedules/",
        "matchup_suffix": "/stats",
    },
}

USER_AGENT = "FullCourtAnalyticsBot/1.0"


# ==========================
# Utility Helpers
# ==========================

def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def http_get(url: str) -> str:
    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    r.raise_for_status()
    return r.text


def safe_write_json(path: Path, obj: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def slug_from_href(href: str) -> str:
    return href.rstrip("/").split("/")[-1]


def parse_date_from_href(href: str) -> Optional[str]:
    m = re.search(r"(\d{4}-\d{2}-\d{2})$", href)
    return m.group(1) if m else None


def slugify_key(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"&", "and", s)
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "key"


# ==========================
# Numeric Parsing
# ==========================

_NUM_RE = re.compile(r"^[\+\-]?\d[\d,]*\.?\d*$")

def parse_numeric(raw: str) -> Optional[float]:
    """
    Converts strings like:
      "53.2%" -> 0.532
      "1.064" -> 1.064
      "+13.7" -> 13.7
      "75.9"  -> 75.9
      "--" or "" -> None
    """
    if raw is None:
        return None
    s = raw.strip()
    if not s or s in {"--", "—"}:
        return None

    # Percent
    if s.endswith("%"):
        val = parse_numeric(s[:-1])
        return (val / 100.0) if val is not None else None

    # Remove commas
    s2 = s.replace(",", "")
    # Allow leading +/-
    if _NUM_RE.match(s2):
        try:
            return float(s2)
        except ValueError:
            return None

    return None


def cell_value(raw: str) -> Dict[str, Any]:
    """
    Standard cell representation:
      {"raw": "53.2%", "value": 0.532}
      {"raw": "KFC Yum! Center", "value": None}
    """
    v = parse_numeric(raw)
    return {"raw": raw, "value": v}


# ==========================
# Matchup Title Normalization
# ==========================

def parse_matchup_teams(title: str) -> Dict[str, Any]:
    """
    TeamRankings schedule titles often look like:
      "Syracuse  at   Louisville"
      "Old Dominion  vs.   UL Monroe"

    Rules:
      - "A at B" => away=A, home=B, neutral_site=False
      - "A vs. B" or "A vs B" => away=A, home=B, neutral_site=True
    """
    t = " ".join(title.split())
    # Normalize separators
    if " at " in t:
        away, home = t.split(" at ", 1)
        return {"away": away.strip(), "home": home.strip(), "neutral_site": False}
    # vs or vs.
    m = re.split(r"\s+vs\.?\s+", t, maxsplit=1)
    if len(m) == 2:
        away, home = m[0], m[1]
        return {"away": away.strip(), "home": home.strip(), "neutral_site": True}

    # fallback (unknown format)
    return {"away": None, "home": None, "neutral_site": None, "raw_title": t}


# ==========================
# Schedule Parsing
# ==========================

@dataclass
class Matchup:
    sport: str
    date: str
    title: str
    href: str
    url: str
    time_local: Optional[str]
    location: Optional[str]
    teams: Dict[str, Any]


def parse_schedule_page(sport: str, html: str) -> List[Matchup]:
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if not table:
        return []

    games: List[Matchup] = []

    for a in table.select("tbody a[href]"):
        href = a.get("href", "")
        if "/matchup/" not in href:
            continue

        title = " ".join(a.get_text(" ", strip=True).split())
        date = parse_date_from_href(href) or "unknown"

        tr = a.find_parent("tr")
        time_local = None
        location = None

        if tr:
            tds = tr.find_all("td")
            if len(tds) >= 5:
                time_local = tds[3].get_text(strip=True) or None
                location = tds[4].get_text(strip=True) or None

        games.append(
            Matchup(
                sport=sport,
                date=date,
                title=title,
                href=href,
                url=urljoin(BASE, href),
                time_local=time_local,
                location=location,
                teams=parse_matchup_teams(title),
            )
        )

    return games


# ==========================
# Matchup Table Parsing
# ==========================

def parse_adv_cell(td) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if not td:
        return out

    if td.select_one(".tr_arrowed_r"):
        out["direction"] = "right"
    elif td.select_one(".tr_arrowed_l"):
        out["direction"] = "left"

    for i in range(1, 6):
        if td.select_one(f".tr_arrowed_{i}"):
            out["level"] = i
            break

    return out


def parse_table(table) -> Dict[str, Any]:
    headers: List[str] = []
    if table.find("thead"):
        headers = [
            th.get_text(" ", strip=True)
            for th in table.find("thead").find_all(["th", "td"])
        ]

    # Identify team columns from headers like: ["Stat", "SYR", "adv", "LOU"]
    # Keep as-is (abbrev), but also expose mapping.
    team_headers = [h for h in headers if h and h.lower() not in {"stat", "adv"}]

    rows: List[Dict[str, Any]] = []
    for tr in table.find("tbody").find_all("tr"):
        tds = tr.find_all("td")
        row: Dict[str, Any] = {}
        for i, td in enumerate(tds):
            key = headers[i] if i < len(headers) else f"col_{i}"
            raw = td.get_text(" ", strip=True)

            if key.lower() == "adv":
                row[key] = parse_adv_cell(td)
            else:
                row[key] = cell_value(raw)

        rows.append(row)

    return {
        "headers": headers,
        "team_headers": team_headers,
        "rows": rows,
    }


def build_feature_map(tables: Dict[str, Any]) -> Dict[str, float]:
    """
    Flattens parsed tables into key->float map.
    Only includes cells where value is numeric (float).

    Key pattern:
      <table_slug>.<stat_slug>.<col_slug>

    Example:
      key_offensive_stats.off_efficiency.syr = 1.064
      key_offensive_stats.effective_fg_pct.lou = 0.565
    """
    feats: Dict[str, float] = {}

    for table_title, t in tables.items():
        table_slug = slugify_key(table_title)
        headers = t.get("headers", [])
        rows = t.get("rows", [])

        for r in rows:
            stat_cell = r.get("Stat") or r.get("stat")
            stat_name = None
            if isinstance(stat_cell, dict):
                stat_name = stat_cell.get("raw")
            elif isinstance(stat_cell, str):
                stat_name = stat_cell

            if not stat_name:
                continue

            stat_slug = slugify_key(stat_name)

            for h in headers:
                if not h or h.lower() in {"stat", "adv"}:
                    continue

                cell = r.get(h)
                if isinstance(cell, dict):
                    v = cell.get("value")
                    if isinstance(v, (int, float)):
                        feats[f"{table_slug}.{stat_slug}.{slugify_key(h)}"] = float(v)

    return feats


def scrape_matchup_page(matchup_url: str, matchup_suffix: str) -> Dict[str, Any]:
    """
    Scrapes the matchup stats/efficiency page and captures ALL <h2> + next <table> pairs
    into a structured tables dict, plus a flattened ML-friendly feature map.
    """
    url = matchup_url.rstrip("/") + matchup_suffix
    html = http_get(url)
    soup = BeautifulSoup(html, "lxml")

    tables: Dict[str, Any] = {}
    for h2 in soup.find_all("h2"):
        title = " ".join(h2.get_text(" ", strip=True).split())
        table = h2.find_next("table")
        if table:
            tables[title] = parse_table(table)

    return {
        "source_url": url,
        "scraped_at_utc": now_utc(),
        "tables": tables,
        "features": build_feature_map(tables),
    }


# ==========================
# Latest Pointer Writer
# ==========================

def write_latest_pointers(root: Path, sport: str, dates: List[str]):
    sport_dir = root / sport

    if not dates:
        safe_write_json(sport_dir / "latest_date.json", {
            "sport": sport,
            "latest_date": None,
            "out_of_season": True,
            "updated_at_utc": now_utc(),
        })
        return

    latest_date = sorted(dates)[-1]

    safe_write_json(sport_dir / "latest_date.json", {
        "sport": sport,
        "latest_date": latest_date,
        "out_of_season": False,
        "schedule_path": f"{sport}/{latest_date}/schedule.json",
        "combined_daily_path": f"{sport}/{latest_date}/combined_daily.json",
        "matchups_dir": f"{sport}/{latest_date}/matchups",
        "updated_at_utc": now_utc(),
    })

    # Mirror latest schedule + combined for convenience
    latest_dir = sport_dir / "latest"
    latest_dir.mkdir(parents=True, exist_ok=True)

    src_schedule = sport_dir / latest_date / "schedule.json"
    if src_schedule.exists():
        safe_write_json(latest_dir / "schedule.json",
                        json.loads(src_schedule.read_text(encoding="utf-8")))

    src_combined = sport_dir / latest_date / "combined_daily.json"
    if src_combined.exists():
        safe_write_json(latest_dir / "combined_daily.json",
                        json.loads(src_combined.read_text(encoding="utf-8")))


# ==========================
# Main Cache Runner
# ==========================

def run_cache(output_dir="data", sports=None):
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    # Default active sports
    selected = sports or ["nba", "ncaab"]

    master_index = {
        "scraped_at_utc": now_utc(),
        "sports": {}
    }

    for sport in selected:
        config = SPORTS[sport]
        schedule_url = config["schedule_url"]
        matchup_suffix = config["matchup_suffix"]

        try:
            html = http_get(schedule_url)
            games = parse_schedule_page(sport, html)
        except Exception as e:
            master_index["sports"][sport] = {
                "schedule_url": schedule_url,
                "error": str(e),
                "out_of_season": True,
            }
            continue

        if not games:
            write_latest_pointers(root, sport, [])
            master_index["sports"][sport] = {
                "schedule_url": schedule_url,
                "out_of_season": True,
            }
            continue

        by_date: Dict[str, List[Matchup]] = {}
        for g in games:
            by_date.setdefault(g.date, []).append(g)

        dates = sorted(by_date.keys())

        master_index["sports"][sport] = {
            "schedule_url": schedule_url,
            "dates": dates,
            "latest_date": dates[-1] if dates else None,
            "out_of_season": False,
        }

        for date_str, day_games in by_date.items():
            day_dir = root / sport / date_str
            matchups_dir = day_dir / "matchups"

            # schedule.json (clean)
            schedule_obj = {
                "sport": sport,
                "date": date_str,
                "scraped_at_utc": now_utc(),
                "games": [
                    {
                        "title": g.title,
                        "slug": slug_from_href(g.href),
                        "url": g.url,
                        "time_local": g.time_local,
                        "location": g.location,
                        "teams": g.teams,
                    }
                    for g in day_games
                ],
            }
            safe_write_json(day_dir / "schedule.json", schedule_obj)

            # Per-matchup cache + combined daily build
            combined = {
                "sport": sport,
                "date": date_str,
                "scraped_at_utc": now_utc(),
                "source": {
                    "schedule_url": schedule_url,
                    "matchup_suffix": matchup_suffix,
                },
                "games": [],
            }

            for g in day_games:
                slug = slug_from_href(g.href)
                matchup_url = g.url.rstrip("/")

                urls = {
                    "matchup": matchup_url,
                    "detail": matchup_url + matchup_suffix,  # the page we scrape
                }

                try:
                    payload = scrape_matchup_page(matchup_url, matchup_suffix)
                    payload.update({
                        "sport": sport,
                        "date": date_str,
                        "slug": slug,
                        "matchup_title": g.title,
                        "teams": g.teams,
                        "time_local": g.time_local,
                        "location": g.location,
                        "urls": urls,
                    })
                except Exception as e:
                    payload = {
                        "sport": sport,
                        "date": date_str,
                        "slug": slug,
                        "matchup_title": g.title,
                        "teams": g.teams,
                        "time_local": g.time_local,
                        "location": g.location,
                        "urls": urls,
                        "error": str(e),
                        "scraped_at_utc": now_utc(),
                        "tables": {},
                        "features": {},
                    }

                safe_write_json(matchups_dir / f"{slug}.json", payload)

                # Add to combined_daily.json (fast load for model)
                combined["games"].append({
                    "slug": slug,
                    "matchup_title": g.title,
                    "teams": g.teams,
                    "time_local": g.time_local,
                    "location": g.location,
                    "urls": urls,
                    "scraped_at_utc": payload.get("scraped_at_utc"),
                    "error": payload.get("error"),
                    "features": payload.get("features", {}),
                    # optional: keep tables for debugging / explainability
                    "tables": payload.get("tables", {}),
                })

                time.sleep(0.5)

            safe_write_json(day_dir / "combined_daily.json", combined)

        write_latest_pointers(root, sport, dates)

    safe_write_json(root / "index.json", master_index)


if __name__ == "__main__":
    run_cache()
