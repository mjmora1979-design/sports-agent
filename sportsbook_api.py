import os
import requests
import datetime

RAPIDAPI_HOST = os.getenv("SPORTSBOOK_RAPIDAPI_HOST", "sportsbook-api2.p.rapidapi.com")
RAPIDAPI_KEY = os.getenv("SPORTSBOOK_RAPIDAPI_KEY")

# Supported sports for safety
SUPPORTED_SPORTS = ["nfl", "ncaaf", "nba", "mlb", "nhl"]

def _headers():
    if not RAPIDAPI_KEY:
        print("[WARN] No RAPIDAPI_KEY in env, requests may fail.")
    return {
        "X-RapidAPI-Host": RAPIDAPI_HOST,
        "X-RapidAPI-Key": RAPIDAPI_KEY or ""
    }

def get_events(sport, start=None, end=None, max_games=None):
    """Fetch events (games) for given sport."""
    if sport not in SUPPORTED_SPORTS:
        raise ValueError(f"Unsupported sport: {sport}")

    url = f"https://{RAPIDAPI_HOST}/events"
    params = {"sport": sport, "region": "us"}
    if start and end:
        params["from"] = start
        params["to"] = end

    try:
        resp = requests.get(url, headers=_headers(), params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        events = data.get("events", [])
        if max_games:
            events = events[:max_games]
        return events
    except Exception as e:
        print("[ERROR] get_events:", e)
        return []

def get_odds(sport, event_ids=None, mode="all"):
    """
    Fetch odds for sport or specific event IDs.
    mode = "open" (first snapshot), "close" (final snapshot), "all" (default).
    """
    if sport not in SUPPORTED_SPORTS:
        raise ValueError(f"Unsupported sport: {sport}")

    url = f"https://{RAPIDAPI_HOST}/odds"
    params = {
        "sport": sport,
        "region": "us",
        "mkt": "h2h,spreads,totals,player_props",
        "oddsFormat": "american"
    }
    if event_ids:
        params["eventIds"] = ",".join(event_ids)
    if mode in ["open", "close"]:
        params["state"] = mode

    try:
        resp = requests.get(url, headers=_headers(), params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get("events", [])
    except Exception as e:
        print("[ERROR] get_odds:", e)
        return []

