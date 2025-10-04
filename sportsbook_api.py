import os
import requests

API_HOST = os.getenv("SPORTSBOOK_RAPIDAPI_HOST", "sportsbook-api2.p.rapidapi.com")
API_KEY = os.getenv("SPORTSBOOK_RAPIDAPI_KEY", "")

BASE_URL = f"https://{API_HOST}"

HEADERS = {
    "X-RapidAPI-Key": API_KEY,
    "X-RapidAPI-Host": API_HOST
}

def get_events(sport, start, end):
    """Pull event IDs for a sport between dates."""
    try:
        url = f"{BASE_URL}/events"
        params = {"sport": sport, "from": start, "to": end, "region": "us"}
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("events", [])
    except Exception as e:
        print("[ERROR] get_events:", e)
        return []

def get_odds(sport, event_ids):
    """Pull odds + props for given events."""
    try:
        url = f"{BASE_URL}/odds"
        params = {"sport": sport, "region": "us", "mkt": "h2h,spreads,totals,player_props"}
        if event_ids:
            params["eventIds"] = ",".join(event_ids)

        resp = requests.get(url, headers=HEADERS, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        return data.get("events", [])
    except Exception as e:
        print("[ERROR] get_odds:", e)
        return []
