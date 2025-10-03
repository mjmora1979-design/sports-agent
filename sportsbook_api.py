import os
import requests

RAPIDAPI_HOST = os.getenv("SPORTSBOOK_RAPIDAPI_HOST", "sportsbook-api2.p.rapidapi.com")
RAPIDAPI_KEY = os.getenv("SPORTSBOOK_RAPIDAPI_KEY", "")

BASE_URL = f"https://{RAPIDAPI_HOST}"

# -------------------------
# Odds Fetcher
# -------------------------

def get_odds(sport="nfl", start=None, end=None, markets=None, books=None):
    """
    Fetch odds from the RapidAPI Sportsbook API.
    Restricts to DraftKings and FanDuel by default.
    """

    # default markets and books
    if markets is None:
        markets = "h2h,spreads,totals,player_props"
    if books is None:
        books = "draftkings,fanduel"

    url = f"{BASE_URL}/odds"

    headers = {"X-RapidAPI-Host": RAPIDAPI_HOST}
    if RAPIDAPI_KEY:
        headers["X-RapidAPI-Key"] = RAPIDAPI_KEY

    params = {
        "sport": sport,
        "region": "us",
        "mkt": markets,
        "oddsFormat": "american",
        "books": books
    }

    # Optionally include timeframe
    if start:
        params["from"] = start
    if end:
        params["to"] = end

    print("[DEBUG] Requesting odds from:", url)
    print("[DEBUG] Params:", params)
    print("[DEBUG] Headers:", {k: v for k, v in headers.items() if k != "X-RapidAPI-Key"})

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=20)
        print("[DEBUG] Response status:", resp.status_code)
        if resp.status_code != 200:
            print("[DEBUG] Response text:", resp.text)
            return []
        return resp.json().get("events", [])
    except Exception as e:
        print("[ERROR] get_odds failed:", e)
        return []
