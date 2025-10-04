import os
import requests
from datetime import datetime, timedelta

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = "sportsbook-api2.p.rapidapi.com"

HEADERS = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": RAPIDAPI_HOST
}

def get_events(sport, start=None, end=None, region="us"):
    """Pull events for a given sport"""
    url = f"https://{RAPIDAPI_HOST}/v1/events"
    params = {
        "sport": sport,
        "region": region
    }
    if start:
        params["from"] = start
    if end:
        params["to"] = end

    try:
        resp = requests.get(url, headers=HEADERS, params=params)
        resp.raise_for_status()
        return resp.json().get("events", [])
    except Exception as e:
        print(f"[ERROR] get_events failed: {e}")
        return []


def get_odds_for_event(event_id, region="us", markets="h2h,spreads,totals,player_props"):
    """Pull odds/props for a single event by ID"""
    url = f"https://{RAPIDAPI_HOST}/v1/odds/{event_id}"
    params = {"region": region, "mkt": markets, "oddsFormat": "american"}

    try:
        resp = requests.get(url, headers=HEADERS, params=params)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[ERROR] get_odds_for_event {event_id} failed: {e}")
        return {}
    

def get_odds(sport, start=None, end=None, max_games=None):
    """Main function to get odds for a sport — loops events → odds"""
    events = get_events(sport, start, end)
    results = []

    for ev in events:
        event_id = ev.get("id")
        if not event_id:
            continue
        odds_data = get_odds_for_event(event_id)
        if odds_data:
            results.append(odds_data)

        if max_games and len(results) >= max_games:
            break

    return results
