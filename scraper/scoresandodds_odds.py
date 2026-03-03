import requests
import json
import os
import re
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from pathlib import Path

BASE_URL = "https://www.scoresandodds.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# ----------------------------
# Helpers
# ----------------------------

def to_float(val):
    """Convert spreads, totals, moneylines to numeric float."""
    if val is None:
        return None
    val = val.strip()

    # Remove o/u prefix for totals
    val = val.replace("o", "").replace("u", "")

    try:
        return float(val)
    except:
        return None


def normalize_team(name):
    return name.strip()


def safe_mkdir(path):
    Path(path).mkdir(parents=True, exist_ok=True)


def timestamp():
    return datetime.now(timezone.utc).isoformat()


# ----------------------------
# Core Scraper
# ----------------------------

def fetch_page(sport="ncaab", date=None):
    url = f"{BASE_URL}/{sport}"
    if date:
        url += f"?date={date}"

    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    return r.text


def parse_events(html):
    soup = BeautifulSoup(html, "html.parser")

    # 1️⃣ Extract JSON-LD structured events
    event_meta = {}
    scripts = soup.find_all("script", type="application/ld+json")

    for s in scripts:
        try:
            data = json.loads(s.string)
            if data.get("@type") == "SportsEvent":
                event_id = str(data.get("identifier"))
                event_meta[event_id] = {
                    "event_id": event_id,
                    "start_time": data.get("startDate"),
                    "home_team": normalize_team(data["homeTeam"]["name"]),
                    "away_team": normalize_team(data["awayTeam"]["name"]),
                    "url": data.get("url")
                }
        except:
            continue

    # 2️⃣ Parse odds tables
    results = []

    event_cards = soup.select(".event-card")

    for card in event_cards:
        card_id = card.get("id", "")
        if "." not in card_id:
            continue

        event_id = card_id.split(".")[1]
        if event_id not in event_meta:
            continue

        rows = card.select("tr.event-card-row")

        odds = {
            "spread": {},
            "total": {},
            "moneyline": {}
        }

        for row in rows:
            side = row.get("data-side")  # home / away

            # Spread
            spread_td = row.select_one('td[data-field="current-spread"]')
            if spread_td:
                val = spread_td.select_one(".data-value")
                price = spread_td.select_one(".data-odds")
                odds["spread"][side] = {
                    "line": to_float(val.text if val else None),
                    "price": to_float(price.text if price else None)
                }

            # Total
            total_td = row.select_one('td[data-field="current-total"]')
            if total_td:
                val = total_td.select_one(".data-value")
                price = total_td.select_one(".data-odds")
                odds["total"][side] = {
                    "line": to_float(val.text if val else None),
                    "price": to_float(price.text if price else None)
                }

            # Moneyline
            ml_td = row.select_one('td[data-field="current-moneyline"]')
            if ml_td:
                val = ml_td.select_one(".data-value")
                odds["moneyline"][side] = to_float(val.text if val else None)

        event = event_meta[event_id]

        model_ready = {
            "event_id": event_id,
            "start_time": event["start_time"],
            "home": {
                "team": event["home_team"],
                "spread": odds["spread"].get("home"),
                "total": odds["total"].get("home"),
                "moneyline": odds["moneyline"].get("home")
            },
            "away": {
                "team": event["away_team"],
                "spread": odds["spread"].get("away"),
                "total": odds["total"].get("away"),
                "moneyline": odds["moneyline"].get("away")
            },
            "scraped_at": timestamp()
        }

        results.append(model_ready)

    return results


# ----------------------------
# Storage Layer
# ----------------------------

def save_snapshot(sport, events):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    base_path = f"data/{sport}/{today}"
    safe_mkdir(base_path)

    combined = []

    for event in events:
        matchup_slug = f"{event['away']['team'].lower().replace(' ', '-')}-at-{event['home']['team'].lower().replace(' ', '-')}"
        matchup_path = f"{base_path}/matchups/{matchup_slug}"
        safe_mkdir(matchup_path)

        # Latest odds file
        latest_file = f"{matchup_path}/odds_latest.json"
        with open(latest_file, "w") as f:
            json.dump(event, f, indent=2)

        # Append to history
        history_file = f"{matchup_path}/odds_history.jsonl"
        with open(history_file, "a") as f:
            f.write(json.dumps(event) + "\n")

        combined.append(event)

    # Combined fast-load file
    combined_file = f"{base_path}/combined_daily.json"
    with open(combined_file, "w") as f:
        json.dump(combined, f, indent=2)

    # Update latest pointer
    with open(f"data/{sport}/latest_date.json", "w") as f:
        json.dump({"latest_date": today}, f)


# ----------------------------
# Runner
# ----------------------------

def run(sport="ncaab", date=None):
    html = fetch_page(sport, date)
    events = parse_events(html)
    save_snapshot(sport, events)
    print(f"Saved {len(events)} events for {sport}")


if __name__ == "__main__":
    run("ncaab")
