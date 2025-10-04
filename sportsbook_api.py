import os
import requests

# ===========================
# Configuration
# ===========================

BASE_URL = "https://sportsbook-api2.p.rapidapi.com/v0"
RAPIDAPI_HOST = "sportsbook-api2.p.rapidapi.com"
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY") or os.getenv("SPORTSBOOK_RAPIDAPI_KEY")

HEADERS = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": RAPIDAPI_HOST
}


# ===========================
# Core API Functions
# ===========================

def list_competitions():
    """
    Get all available competitions (NFL, NBA, etc.)
    Example endpoint: /v0/competitions
    """
    url = f"{BASE_URL}/competitions"
    print("[DEBUG] GET", url)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        print("[DEBUG] Status:", resp.status_code)
        if resp.status_code == 200:
            data = resp.json()
            comps = data.get("competitions", [])
            print(f"[DEBUG] Found {len(comps)} competitions")
            return comps
        else:
            return {"error": f"HTTP {resp.status_code}", "text": resp.text}
    except Exception as e:
        print("[ERROR] list_competitions:", e)
        return {"error": str(e)}


def get_events_for_competition(competition_key: str, event_type: str = "MATCH"):
    """
    Get all events under a competition (e.g. NFL games)
    Example endpoint:
    /v0/competitions/{competitionKey}/events?eventType=MATCH
    """
    url = f"{BASE_URL}/competitions/{competition_key}/events"
    params = {"eventType": event_type}
    print("[DEBUG] GET", url, params)
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
        print("[DEBUG] Status:", resp.status_code)
        if resp.status_code == 200:
            data = resp.json()
            events = data.get("events", [])
            print(f"[DEBUG] Retrieved {len(events)} events")
            return events
        else:
            return {"error": f"HTTP {resp.status_code}", "text": resp.text}
    except Exception as e:
        print("[ERROR] get_events_for_competition:", e)
        return {"error": str(e)}


def get_events_by_keys(event_keys: list):
    """
    Get detailed info for specific eventKeys
    Example endpoint:
    /v0/events?eventKeys=["abc123","def456"]&returnType=array
    """
    if not event_keys:
        return {"events": []}

    url = f"{BASE_URL}/events"
    params = {"eventKeys": event_keys, "returnType": "array"}
    print("[DEBUG] GET", url, params)
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
        print("[DEBUG] Status:", resp.status_code)
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"error": f"HTTP {resp.status_code}", "text": resp.text}
    except Exception as e:
        print("[ERROR] get_events_by_keys:", e)
        return {"error": str(e)}


def get_markets(event_key: str):
    """
    Get all available markets (odds, props, etc.) for a given event.
    Example endpoint:
    /v0/events/{eventKey}/markets
    """
    url = f"{BASE_URL}/events/{event_key}/markets"
    print("[DEBUG] GET", url)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        print("[DEBUG] Status:", resp.status_code)
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"error": f"HTTP {resp.status_code}", "text": resp.text}
    except Exception as e:
        print("[ERROR] get_markets:", e)
        return {"error": str(e)}


# ===========================
# Optional Future Endpoints
# ===========================

def get_market_outcomes(market_key: str):
    """
    Get all outcomes for a given market (optional).
    Example endpoint:
    /v0/markets/{marketKey}/outcomes
    """
    url = f"{BASE_URL}/markets/{market_key}/outcomes"
    print("[DEBUG] GET", url)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"error": f"HTTP {resp.status_code}", "text": resp.text}
    except Exception as e:
        print("[ERROR] get_market_outcomes:", e)
        return {"error": str(e)}


def get_participant_statistics(participant_key: str):
    """
    Retrieve player or team statistics (optional).
    Example endpoint:
    /v0/participants/{participantKey}/statistics
    """
    url = f"{BASE_URL}/participants/{participant_key}/statistics"
    print("[DEBUG] GET", url)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"error": f"HTTP {resp.status_code}", "text": resp.text}
    except Exception as e:
        print("[ERROR] get_participant_statistics:", e)
        return {"error": str(e)}


def get_advantages():
    """
    Retrieve sportsbook's internal 'advantages' data (optional).
    Example endpoint:
    /v0/advantages
    """
    url = f"{BASE_URL}/advantages"
    print("[DEBUG] GET", url)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"error": f"HTTP {resp.status_code}", "text": resp.text}
    except Exception as e:
        print("[ERROR] get_advantages:", e)
        return {"error": str(e)}
