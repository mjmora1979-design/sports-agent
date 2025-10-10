"""
odds_api_collector.py
---------------------
Odds API integration for weekly NFL line snapshots.
Pulls opening and closing odds with minimal API calls.
"""

import os
import requests
import datetime
import json
from pathlib import Path

# Load your API key from environment variable
ODDS_API_KEY = os.getenv("ODDS_API_KEY")

BASE_URL = "https://api.the-odds-api.com/v4/sports"
SPORT_KEY = "americanfootball_nfl"
MARKETS = ["h2h", "spreads", "totals"]
BOOKMAKERS = ["draftkings", "fanduel"]  # adjust as needed
REGION = "us"
CACHE_FILE = Path("cached_odds.json")


def fetch_odds(snapshot_type="opening"):
    """Fetch NFL odds snapshot (opening or closing)."""
    url = f"{BASE_URL}/{SPORT_KEY}/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": REGION,
        "markets": ",".join(MARKETS),
        "bookmakers": ",".join(BOOKMAKERS),
        "oddsFormat": "american",
        "dateFormat": "iso",
    }

    print(f"[INFO] Fetching {snapshot_type} odds from The Odds API...")
    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    # Save locally for caching/backtesting
    save_snapshot(data, snapshot_type)
    print(f"[INFO] Retrieved {len(data)} events from Odds API.")
    return data


def save_snapshot(data, snapshot_type):
    """Cache snapshot to local JSON file with timestamp."""
    timestamp = datetime.datetime.utcnow().isoformat()
    payload = {
        "snapshot_type": snapshot_type,
        "timestamp_utc": timestamp,
        "data": data,
    }

    if CACHE_FILE.exists():
        with open(CACHE_FILE, "r") as f:
            cache = json.load(f)
    else:
        cache = {}

    cache[snapshot_type] = payload

    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

    print(f"[CACHE] Saved {snapshot_type} snapshot to {CACHE_FILE}")


def load_cached(snapshot_type):
    """Load cached odds if available."""
    if not CACHE_FILE.exists():
        print("[WARN] No cache file found.")
        return None

    with open(CACHE_FILE, "r") as f:
        cache = json.load(f)

    return cache.get(snapshot_type, {}).get("data")


def get_or_fetch(snapshot_type):
    """
    Use cached odds if available; otherwise fetch from API.
    """
    cached = load_cached(snapshot_type)
    if cached:
        print(f"[INFO] Using cached {snapshot_type} odds.")
        return cached
    else:
        return fetch_odds(snapshot_type)


if __name__ == "__main__":
    # Example manual run
    # Fetch opening odds early in week:
    opening_data = get_or_fetch("opening")

    # Later in week (e.g. Sunday morning):
    # closing_data = fetch_odds("closing")
