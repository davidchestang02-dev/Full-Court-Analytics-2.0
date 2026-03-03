#!/usr/bin/env python3
"""
TeamRankings daily schedule -> matchup efficiency table cache.

Outputs:
data/
  index.json                                  # top-level index
  nba/2026-03-03/schedule.json
  nba/2026-03-03/matchups/<slug>.json
  nfl/...
  ncaaf/...
  mlb/...

Designed to be run daily via GitHub Actions.
"""

from __future__ import annotations

import json
import os
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
    # You asked for: NBA, MLB, NFL, NCAAF
    "nba": {
        "schedule_url": f"{BASE}/nba/schedules/",
        "matchup_efficiency_suffix": "/efficiency",
    },
    "mlb": {
        "schedule_url": f"{BASE}/mlb/schedules/",
        "matchup_efficiency_suffix": "/stats",  # MLB may not have "efficiency" in same way; adjust if needed
    },
    "nfl": {
        "schedule_url": f"{BASE}/nfl/schedules/",
        "matchup_efficiency_suffix": "/stats",  # adjust if you prefer another subpage
    },
    "ncaaf": {
        "schedule_url": f"{BASE}/college-football/schedules/",
        "matchup_efficiency_suffix": "/stats",  # adjust if needed
    },
    # Optional: you’re already working NCAAB
    "ncaab": {
        "schedule_url": f"{BASE}/ncb/schedules/",
        "matchup_efficiency_suffix": "/efficiency",
    },
}

UA = "Mozilla/5.0 (compatible; FullCourtAnalyticsBot/1.0; +https://github.com/yourorg/yourrepo)"


@dataclass
class MatchupLink:
    sport: str
    date: str            # YYYY-MM-DD
    title: str           # "Syracuse at Louisville"
    href: str            # "/ncaa-basketball/matchup/orange-cardinals-2026-03-03"
    url: str             # absolute
    time_local: Optional[str] = None
    location: Optional[str] = None


def http_get(url: str, timeout: int = 30) -> str:
    r = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
    r.raise_for_status()
    return r.text


def safe_write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def parse_date_from_matchup_href(href: str) -> Optional[str]:
    # Many matchup slugs end with YYYY-MM-DD
    m = re.search(r"(\d{4}-\d{2}-\d{2})$", href)
    return m.group(1) if m else None


def parse_schedule_page(sport: str, html: str) -> List[MatchupLink]:
    """
    Grabs all matchup anchors from the schedule table.
    TeamRankings schedule pages use a table with links in the Matchup column. :contentReference[oaicite:2]{index=2}
    """
    soup = BeautifulSoup(html, "lxml")

    table = soup.find("table", class_=lambda c: c and "tr-table" in c)
    if not table:
        # fallback: first table
        table = soup.find("table")
    if not table:
        return []

    links: List[MatchupLink] = []
    for a in table.select("tbody a[href]"):
        href = a.get("href", "").strip()
        if not href.startswith("/"):
            continue
        if "/matchup/" not in href:
            continue

        date = parse_date_from_matchup_href(href) or ""
        title = " ".join(a.get_text(" ", strip=True).split())

        # Try to pick time/location from row columns if present
        tr = a.find_parent("tr")
        time_local = None
        location = None
        if tr:
            tds = tr.find_all("td")
            # schedule pages often have: rank, hotness, matchup, time, location
            if len(tds) >= 5:
                time_local = tds[3].get_text(" ", strip=True) or None
                location = tds[4].get_text(" ", strip=True) or None

        links.append(
            MatchupLink(
                sport=sport,
                date=date,
                title=title,
                href=href,
                url=urljoin(BASE, href),
                time_local=time_local,
                location=location,
            )
        )
    return links


def parse_adv_cell(td) -> Dict[str, Any]:
    """
    Extract the 'adv' arrow direction + magnitude when present.
    Example structure includes tr_arrowed_r + tr_arrowed_2, etc.
    """
    out: Dict[str, Any] = {}
    if not td:
        return out
    cls = " ".join(td.get("class", [])).strip()
    if "gz_a_adv" not in cls:
        return out

    # Direction: right = advantage to right team; left = advantage to left team
    direction = None
    if td.select_one(".tr_arrowed_r"):
        direction = "right"
    elif td.select_one(".tr_arrowed_l"):
        direction = "left"

    # Level: find tr_arrowed_1..4
    level = None
    for i in range(1, 6):
        if td.select_one(f".tr_arrowed_{i}"):
            level = i
            break

    out["adv_direction"] = direction
    out["adv_level"] = level
    return out


def html_table_to_rows(table) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Converts a TR table into:
      headers: ["Stat", "SYR", "adv", "LOU"]
      rows: [{...}]
    Handles adv arrow cell specially.
    """
    headers = []
    thead = table.find("thead")
    if thead:
        headers = [th.get_text(" ", strip=True) for th in thead.find_all(["th", "td"])]

    body_rows: List[Dict[str, Any]] = []
    tbody = table.find("tbody")
    if not tbody:
        return headers, body_rows

    for tr in tbody.find_all("tr"):
        tds = tr.find_all("td")
        if not tds:
            continue

        # Build row keyed by headers if possible; else index-based
        row: Dict[str, Any] = {}
        for idx, td in enumerate(tds):
            key = headers[idx] if idx < len(headers) and headers[idx] else f"col_{idx}"
            text = td.get_text(" ", strip=True)

            if key.lower() == "adv":
                row[key] = parse_adv_cell(td)
            else:
                row[key] = text

        body_rows.append(row)

    return headers, body_rows


def find_table_by_h2(soup: BeautifulSoup, h2_text: str) -> Optional[Any]:
    """
    Finds the FIRST <h2> whose normalized text matches h2_text, then the next table.
    """
    def norm(s: str) -> str:
        return re.sub(r"\s+", " ", s.strip()).lower()

    target = norm(h2_text)

    for h2 in soup.find_all("h2"):
        if norm(h2.get_text(" ", strip=True)) == target:
            # Table may be next sibling or within parent
            table = h2.find_next("table")
            if table:
                return table
    return None


def parse_matchup_team_names_from_h2(h2) -> str:
    return re.sub(r"\s+", " ", h2.get_text(" ", strip=True)).strip()


def scrape_ncaab_efficiency_tables(matchup_efficiency_url: str) -> Dict[str, Any]:
    """
    Pulls the 4 tables you described:
      - Key Offensive Stats
      - Key Defensive Stats
      - <TeamA> vs <TeamB> Offensive Efficiency
      - <TeamA> vs <TeamB> Defensive Efficiency

    These headings appear on the matchup efficiency page. :contentReference[oaicite:3]{index=3}
    """
    html = http_get(matchup_efficiency_url)
    soup = BeautifulSoup(html, "lxml")

    tables_out: Dict[str, Any] = {
        "source_url": matchup_efficiency_url,
        "scraped_at_utc": datetime.now(timezone.utc).isoformat(),
        "tables": {},
    }

    # Simple ones
    for title in ["Key Offensive Stats", "Key Defensive Stats"]:
        table = find_table_by_h2(soup, title)
        if table:
            headers, rows = html_table_to_rows(table)
            tables_out["tables"][title] = {"headers": headers, "rows": rows}

    # Dynamic ones: find the specific Offensive/Defensive Efficiency section titles
    # We’ll scan all h2 and capture the ones ending in "Offensive Efficiency" / "Defensive Efficiency"
    for h2 in soup.find_all("h2"):
        h2_name = parse_matchup_team_names_from_h2(h2)
        if h2_name.endswith("Offensive Efficiency") or h2_name.endswith("Defensive Efficiency"):
            table = h2.find_next("table")
            if table:
                headers, rows = html_table_to_rows(table)
                tables_out["tables"][h2_name] = {"headers": headers, "rows": rows}

    return tables_out


def scrape_matchup(sport: str, matchup_url: str) -> Dict[str, Any]:
    """
    For NBA/NFL/MLB/NCAAF you may want different pages/tables.
    For now:
      - If sport has matchup_efficiency_suffix '/efficiency', scrape the 4 NCAAB-style tables.
      - Otherwise, store the raw URL + a placeholder. You can extend per-sport parsing later.
    """
    suffix = SPORTS[sport]["matchup_efficiency_suffix"]
    target_url = matchup_url.rstrip("/") + suffix

    if suffix == "/efficiency":
        return scrape_ncaab_efficiency_tables(target_url)

    # Generic capture (extend later per sport)
    return {
        "source_url": target_url,
        "scraped_at_utc": datetime.now(timezone.utc).isoformat(),
        "note": f"No sport-specific table parser implemented for suffix={suffix}. Extend scrape_matchup().",
    }


def group_matchups_by_date(matchups: List[MatchupLink]) -> Dict[str, List[MatchupLink]]:
    out: Dict[str, List[MatchupLink]] = {}
    for m in matchups:
        if not m.date:
            # if date is missing, group under "unknown"
            out.setdefault("unknown", []).append(m)
        else:
            out.setdefault(m.date, []).append(m)
    return out


def slug_from_href(href: str) -> str:
    # "/ncaa-basketball/matchup/orange-cardinals-2026-03-03" -> "orange-cardinals-2026-03-03"
    return href.rstrip("/").split("/")[-1]


def run_cache(output_dir: str = "data", sports: Optional[List[str]] = None, sleep_s: float = 0.6) -> None:
    out_root = Path(output_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    selected_sports = sports or [k for k in SPORTS.keys() if k in ("nba", "mlb", "nfl", "ncaaf", "ncaab")]

    top_index: Dict[str, Any] = {
        "scraped_at_utc": datetime.now(timezone.utc).isoformat(),
        "sports": {},
    }

    for sport in selected_sports:
        sched_url = SPORTS[sport]["schedule_url"]
        sched_html = http_get(sched_url)
        matchups = parse_schedule_page(sport, sched_html)
        by_date = group_matchups_by_date(matchups)

        top_index["sports"][sport] = {
            "schedule_url": sched_url,
            "dates": sorted(by_date.keys()),
        }

        for date_str, day_games in by_date.items():
            day_dir = out_root / sport / date_str
            schedule_path = day_dir / "schedule.json"

            schedule_obj = {
                "sport": sport,
                "date": date_str,
                "source_url": sched_url,
                "scraped_at_utc": datetime.now(timezone.utc).isoformat(),
                "games": [
                    {
                        "title": g.title,
                        "href": g.href,
                        "url": g.url,
                        "time_local": g.time_local,
                        "location": g.location,
                        "slug": slug_from_href(g.href),
                    }
                    for g in day_games
                ],
            }
            safe_write_json(schedule_path, schedule_obj)

            # Scrape each matchup page and cache it
            for g in day_games:
                mslug = slug_from_href(g.href)
                matchup_path = day_dir / "matchups" / f"{mslug}.json"

                try:
                    payload = scrape_matchup(sport, g.url)
                    payload.update({
                        "sport": sport,
                        "date": date_str,
                        "matchup_title": g.title,
                        "matchup_url": g.url,
                        "slug": mslug,
                    })
                    safe_write_json(matchup_path, payload)
                except Exception as e:
                    safe_write_json(matchup_path, {
                        "sport": sport,
                        "date": date_str,
                        "matchup_title": g.title,
                        "matchup_url": g.url,
                        "slug": mslug,
                        "error": str(e),
                        "scraped_at_utc": datetime.now(timezone.utc).isoformat(),
                    })

                time.sleep(sleep_s)

    safe_write_json(out_root / "index.json", top_index)


if __name__ == "__main__":
    # Example local run:
    #   python scraper/teamrankings_cache.py
    # Or limit sports:
    #   python scraper/teamrankings_cache.py nba ncaab
    import sys
    args = sys.argv[1:]
    if args:
        run_cache(sports=args)
    else:
        run_cache()
