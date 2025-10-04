import os, requests, datetime

RAPIDAPI_HOST = os.getenv("SPORTSBOOK_RAPIDAPI_HOST", "sportsbook-api2.p.rapidapi.com")
RAPIDAPI_KEY = os.getenv("SPORTSBOOK_RAPIDAPI_KEY")

BASE_URL = f"https://{RAPIDAPI_HOST}"

def get_headers():
    return {
        "X-RapidAPI-Host": RAPIDAPI_HOST,
        "X-RapidAPI-Key": RAPIDAPI_KEY
    }

def get_odds(sport, from_date=None, to_date=None, force_direct=False):
    """
    Pull odds either directly (/odds) or with events+odds if available.
    """
    url = f"{BASE_URL}/odds"
    params = {
        "sport": sport,
        "region": "us",
        "mkt": "h2h,spreads,totals,player_props",
        "oddsFormat": "american"
    }

    try:
        print(f"[DEBUG] Requesting odds from {url} (force_direct={force_direct})")
        resp = requests.get(url, headers=get_headers(), params=params, timeout=20)
        resp.raise_for_status()
        return resp.json().get("events", [])
    except Exception as e:
        print(f"[ERROR] get_odds: {e}")
        return []
