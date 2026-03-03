#!/usr/bin/env python3
"""
TeamRankings Daily Cache Engine
--------------------------------

Outputs:
data/
  index.json
  nba/
    latest_date.json
    latest/schedule.json
    YYYY-MM-DD/
      schedule.json
      matchups/<slug>.json
  ncaab/
    ...

Season-aware. Safe for GitHub Actions daily runs.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
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

def now_utc():
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
            )
        )

    return games


# ==========================
# Matchup Table Parsing
# ==========================

def parse_adv_cell(td):
    out = {}
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


def parse_table(table):
    headers = []
    if table.find("thead"):
        headers = [
            th.get_text(" ", strip=True)
            for th in table.find("thead").find_all(["th", "td"])
        ]

    rows = []
    for tr in table.find("tbody").find_all("tr"):
        tds = tr.find_all("td")
        row = {}
        for i, td in enumerate(tds):
            key = headers[i] if i < len(headers) else f"col_{i}"
            if key.lower() == "adv":
                row[key] = parse_adv_cell(td)
            else:
                row[key] = td.get_text(" ", strip=True)
        rows.append(row)

    return {"headers": headers, "rows": rows}


def scrape_efficiency_page(url: str) -> Dict[str, Any]:
    html = http_get(url)
    soup = BeautifulSoup(html, "lxml")

    data = {
        "source_url": url,
        "scraped_at_utc": now_utc(),
        "tables": {}
    }

    for h2 in soup.find_all("h2"):
        title = " ".join(h2.get_text(" ", strip=True).split())
        table = h2.find_next("table")
        if table:
            data["tables"][title] = parse_table(table)

    return data


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
        "matchups_dir": f"{sport}/{latest_date}/matchups",
        "updated_at_utc": now_utc(),
    })

    src = sport_dir / latest_date / "schedule.json"
    if src.exists():
        latest_dir = sport_dir / "latest"
        latest_dir.mkdir(parents=True, exist_ok=True)
        safe_write_json(latest_dir / "schedule.json",
                        json.loads(src.read_text(encoding="utf-8")))


# ==========================
# Main Cache Runner
# ==========================

def run_cache(output_dir="data", sports=None):
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    selected = sports or ["nba", "ncaab"]

    master_index = {
        "scraped_at_utc": now_utc(),
        "sports": {}
    }

    for sport in selected:
        config = SPORTS[sport]
        schedule_url = config["schedule_url"]

        try:
            html = http_get(schedule_url)
            games = parse_schedule_page(sport, html)
        except Exception as e:
            master_index["sports"][sport] = {
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

        by_date = {}
        for g in games:
            by_date.setdefault(g.date, []).append(g)

        dates = sorted(by_date.keys())

        master_index["sports"][sport] = {
            "schedule_url": schedule_url,
            "dates": dates,
            "out_of_season": False,
        }

        for date_str, day_games in by_date.items():
            day_dir = root / sport / date_str
            matchups_dir = day_dir / "matchups"

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
                    }
                    for g in day_games
                ],
            }

            safe_write_json(day_dir / "schedule.json", schedule_obj)

            for g in day_games:
                slug = slug_from_href(g.href)
                matchup_url = g.url.rstrip("/") + config["matchup_suffix"]

                try:
                    payload = scrape_efficiency_page(matchup_url)
                    payload.update({
                        "sport": sport,
                        "date": date_str,
                        "matchup_title": g.title,
                        "slug": slug,
                    })
                except Exception as e:
                    payload = {
                        "sport": sport,
                        "date": date_str,
                        "matchup_title": g.title,
                        "slug": slug,
                        "error": str(e),
                        "scraped_at_utc": now_utc(),
                    }

                safe_write_json(matchups_dir / f"{slug}.json", payload)
                time.sleep(0.5)

        write_latest_pointers(root, sport, dates)

    safe_write_json(root / "index.json", master_index)


if __name__ == "__main__":
    run_cache()
