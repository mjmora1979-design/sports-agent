# sportsbook_api.py
import os
import requests
import datetime

# ------------------------------------------------
# Config
# ------------------------------------------------
RAPIDAPI_HOST = os.getenv("SPORTSBOOK_RAPIDAPI_HOST", "sportsbook-api2.p.rapidapi.com")
RAPIDAPI_KEY = os.getenv("SPORTSBOOK_RAPIDAPI_KEY")

HEADERS = {
    "X-RapidAPI-Host": RAPIDAPI_HOST,
    "X-RapidAPI-Key": RAPIDAPI_KEY
}

# ------------------------------------------------
# Fetch odds directly (no /events anymore)
# ------------------------------------------------
def get_odds(sport: str, days: int = 7, markets=None):
    """
    Pull odds (moneyline, spreads, totals, props) for given sport.
    Defaults to 7 days ahead. Removes /events call.
    """
    if markets is None:
        markets = ["h2h", "spreads", "totals", "player_props"]

    base_url = f"https://{RAPIDAPI_HOST}/odds"

    start = datetime.datetime.utcnow()
    end = start + datetime.timedelta(days=days)

    params = {
        "sport": sport,
        "region": "us",
        "mkt": ",".join(markets),
        "oddsFormat": "american"
        # ❌ removed from/to because not supported by odds endpoint
    }

    try:
        print(f"[DEBUG] Requesting odds from: {base_url}")
        print(f"[DEBUG] Params: {params}")

        resp = requests.get(base_url, headers=HEADERS, params=params, timeout=15)
        resp.raise_for_status()

        data = resp.json()
        print(f"[DEBUG] Odds response keys: {list(data.keys())}")

        # Return as-is for sports_agent.py to process
        return data.get("events", []) or data.get("games", []) or []
    except Exception as e:
        print(f"[ERROR] get_odds failed: {e}")
        return []
