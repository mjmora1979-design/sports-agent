import os
import requests

# === CONFIG ===
BASE_URL = "https://sportsbook-api2.p.rapidapi.com/v0"
RAPIDAPI_HOST = "sportsbook-api2.p.rapidapi.com"
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

HEADERS = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": RAPIDAPI_HOST
}

def get_events(sport: str):
    """
    Fetch events for a given sport from the Sportsbook API 2.
    Example endpoint: /v0/events?sport=nfl
    """
    url = f"{BASE_URL}/events"
    params = {"sport": sport}

    print(f"[DEBUG] GET {url} {params}")
    print(f"[DEBUG] Headers: {HEADERS}")

    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
        print(f"[DEBUG] Response Code: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"[DEBUG] Retrieved {len(data.get('events', []))} events")
            return data
        else:
            return {"error": f"HTTP {resp.status_code}", "text": resp.text}
    except Exception as e:
        print(f"[ERROR] get_events exception: {e}")
        return {"error": str(e)}

def get_odds(sport: str):
    """
    Fetch odds for a given sport.
    Example endpoint: /v0/odds?sport=nfl
    """
    url = f"{BASE_URL}/odds"
    params = {"sport": sport}

    print(f"[DEBUG] GET {url} {params}")
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
        print(f"[DEBUG] Response Code: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"[DEBUG] Retrieved {len(data.get('odds', []))} odds entries")
            return data
        else:
            return {"error": f"HTTP {resp.status_code}", "text": resp.text}
    except Exception as e:
        print(f"[ERROR] get_odds exception: {e}")
        return {"error": str(e)}
