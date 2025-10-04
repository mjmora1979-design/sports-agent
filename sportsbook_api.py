import os
import requests
import datetime

# Pull environment variables
API_HOST = os.environ.get("SPORTSBOOK_RAPIDAPI_HOST")
API_KEY = os.environ.get("SPORTSBOOK_RAPIDAPI_KEY")

# Headers for RapidAPI
HEADERS = {
    "x-rapidapi-host": API_HOST,
    "x-rapidapi-key": API_KEY,
    "accept": "application/json"
}

def _debug_headers():
    """Print key debug info without exposing full secrets."""
    print(f"[DEBUG] Host = {HEADERS.get('x-rapidapi-host')}")
    print(f"[DEBUG] API key present? {bool(HEADERS.get('x-rapidapi-key'))}")

def get_events(sport: str, region: str = "us", days: int = 7):
    """Fetch events (games) for a sport."""
    _debug_headers()
    try:
        now = datetime.datetime.utcnow()
        end = now + datetime.timedelta(days=days)
        params = {
            "sport": sport,
            "region": region,
            "from": now.isoformat(),
            "to": end.isoformat()
        }
        url = f"https://{API_HOST}/v1/events"
        print(f"[DEBUG] Requesting events from: {url}")
        print(f"[DEBUG] Params: {params}")
        res = requests.get(url, headers=HEADERS, params=params, timeout=15)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f"[ERROR] get_events failed: {e}")
        return {"events": []}

def get_odds(sport: str, region: str = "us", markets: str = "h2h,spreads,totals,player_props"):
    """Fetch odds for a sport."""
    _debug_headers()
    try:
        params = {
            "sport": sport,
            "region": region,
            "mkt": markets,
            "oddsFormat": "american"
        }
        url = f"https://{API_HOST}/v1/odds"
        print(f"[DEBUG] Requesting odds from: {url}")
        print(f"[DEBUG] Params: {params}")
        res = requests.get(url, headers=HEADERS, params=params, timeout=15)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f"[ERROR] get_odds failed: {e}")
        return {"odds": []}
