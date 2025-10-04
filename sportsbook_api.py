# sportsbook_api.py
# Unified RapidAPI Sportsbook API client
# Supports events, odds, props, and advantages (DraftKings + FanDuel only)

import os
import requests
import json

RAPIDAPI_HOST = "sportsbook-api2.p.rapidapi.com"
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

if not RAPIDAPI_KEY:
    print("[ERROR] RAPIDAPI_KEY not found in environment variables!")

BASE_URLS = {
    "v0": f"https://{RAPIDAPI_HOST}/v0",
    "v1": f"https://{RAPIDAPI_HOST}/v1"
}

HEADERS = {
    "x-rapidapi-host": RAPIDAPI_HOST,
    "x-rapidapi-key": RAPIDAPI_KEY
}

# -------------------------------------------------------------
# Helper function to make a request and safely handle responses
# -------------------------------------------------------------
def safe_request(url, params=None):
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)
        print(f"[DEBUG] GET {url} -> {response.status_code}")
        if response.status_code == 200:
            return response.json()
        else:
            return {"status": response.status_code, "url": url, "error": response.text}
    except Exception as e:
        print(f"[ERROR] Request failed: {e}")
        return {"error": str(e), "url": url}

# -------------------------------------------------------------
# 1️⃣ Competitions and Events
# -------------------------------------------------------------
def get_competitions():
    """Fetch all available competitions (NFL, NBA, etc.)."""
    url = f"{BASE_URLS['v0']}/competitions/"
    return safe_request(url)

def get_events(competition_key: str):
    """Fetch all events for a competition (e.g., Q63E-wddv-ddp4 for NFL)."""
    url = f"{BASE_URLS['v0']}/competitions/{competition_key}/events"
    params = {"eventType": "MATCH"}
    return safe_request(url, params=params)

def get_event_details(event_key: str):
    """Fetch specific event details by key."""
    url = f"{BASE_URLS['v0']}/events/{event_key}"
    return safe_request(url)

# -------------------------------------------------------------
# 2️⃣ Odds & Props Data
# -------------------------------------------------------------
def get_event_markets(event_key: str):
    """
    Fetch markets (odds + props) for a given event.
    This often includes team props, player props, totals, etc.
    """
    url = f"{BASE_URLS['v0']}/events/{event_key}/markets"
    data = safe_request(url)

    # Filter to only DraftKings and FanDuel
    if isinstance(data, dict) and "markets" in data:
        filtered = []
        for market in data["markets"]:
            books = [b for b in market.get("bookmakers", []) if b["key"].lower() in ["draftkings", "fanduel"]]
            if books:
                market["bookmakers"] = books
                filtered.append(market)
        data["markets"] = filtered
    return data

def get_market_outcomes(market_key: str):
    """Fetch outcome odds for a given market (usually v1)."""
    url = f"{BASE_URLS['v1']}/markets/{market_key}/outcomes"
    return safe_request(url)

# -------------------------------------------------------------
# 3️⃣ Advantages / Insights
# -------------------------------------------------------------
def get_advantages():
    """Fetch advantage insights (model edge, win prob, etc.)."""
    url = f"{BASE_URLS['v1']}/advantages/"
    return safe_request(url)

# -------------------------------------------------------------
# 4️⃣ Wrapper for multi-step debugging
# -------------------------------------------------------------
def test_all_endpoints(competition_key="Q63E-wddv-ddp4", sample_event=None):
    """Test all key API routes for debugging and validation."""
    results = {}

    print("[DEBUG] Fetching competitions...")
    results["competitions"] = get_competitions()

    print(f"[DEBUG] Fetching events for {competition_key}...")
    events_data = get_events(competition_key)
    results["events"] = events_data

    if sample_event:
        print(f"[DEBUG] Fetching event details and markets for {sample_event}...")
        results["event_details"] = get_event_details(sample_event)
        results["markets"] = get_event_markets(sample_event)
        results["advantages"] = get_advantages()

    return results

# -------------------------------------------------------------
# 5️⃣ Main Debug Mode
# -------------------------------------------------------------
if __name__ == "__main__":
    print("[DEBUG] Starting API self-test...")
    test_data = test_all_endpoints()
    print(json.dumps(test_data, indent=2))
