import os
import requests
import datetime

API_HOST = os.getenv("SPORTSBOOK_RAPIDAPI_HOST")
API_KEY = os.getenv("SPORTSBOOK_RAPIDAPI_KEY")

BASE_URL = f"https://{API_HOST}"

def _headers():
    return {
        "X-RapidAPI-Host": API_HOST,
        "X-RapidAPI-Key": API_KEY
    }

def get_events(sport, start=None, end=None, region="us"):
    """Fetch events list for given sport."""
    url = f"{BASE_URL}/events"
    params = {"sport": sport, "region": region}
    if start: params["from"] = start
    if end: params["to"] = end

    resp = requests.get(url, headers=_headers(), params=params)
    resp.raise_for_status()
    return resp.json().get("events", [])

def get_odds(sport, event_ids=None, markets=None, region="us", odds_format="american"):
    """Fetch odds/markets/props for given sport or event_ids."""
    url = f"{BASE_URL}/odds"
    params = {"sport": sport, "region": region, "oddsFormat": odds_format}
    if markets:
        params["mkt"] = ",".join(markets)
    if event_ids:
        params["eventIds"] = ",".join(event_ids)

    resp = requests.get(url, headers=_headers(), params=params)
    resp.raise_for_status()
    return resp.json().get("odds", [])
