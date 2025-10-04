# sportsbook_api.py
import os
import requests
import datetime

RAPIDAPI_HOST = os.getenv("SPORTSBOOK_RAPIDAPI_HOST", "sportsbook-api2.p.rapidapi.com")
RAPIDAPI_KEY = os.getenv("SPORTSBOOK_RAPIDAPI_KEY")  # set in Render env

# Simple in-memory cache (resets each deploy)
_odds_cache = {}
_last_fetch = None

def _make_request(endpoint, params):
    """Helper to make API request with debug logging."""
    url = f"https://{RAPIDAPI_HOST}/{endpoint}"
    headers = {
        "X-RapidAPI-Host": RAPIDAPI_HOST,
        "X-RapidAPI-Key": RAPIDAPI_KEY
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)

        # ✅ Debug logs to Render output
        print(f"[DEBUG] Requesting: {url}")
        print(f"[DEBUG] Params: {params}")
        print(f"[DEBUG] Status: {resp.status_code}")
        print(f"[DEBUG] Response text (first 500 chars): {resp.text[:500]}")

        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[ERROR] {endpoint} failed:", e)
        return {}

def get_odds(sport="nfl", days_ahead=7, force_refresh=False):
    """
    Fetch odds & props for a sport.
    Uses simple once-per-day cache unless force_refresh=True.
    """
    global _odds_cache, _last_fetch

    today = datetime.date.today()
    if not force_refresh and _last_fetch == today and sport in _odds_cache:
        print(f"[DEBUG] Returning cached odds for {sport}")
        return _odds_cache[sport]

    # Build time window
    start = datetime.datetime.utcnow().isoformat()
    end = (datetime.datetime.utcnow() + datetime.timedelta(days=days_ahead)).isoformat()

    # 🔑 Odds endpoint (first test here)
    params = {
        "sport": sport,
        "region": "us",
        "mkt": "h2h,spreads,totals,player_props",
        "oddsFormat": "american"
    }
    data = _make_request("odds", params)

    # Save to cache
    _odds_cache[sport] = data
    _last_fetch = today
    return data
