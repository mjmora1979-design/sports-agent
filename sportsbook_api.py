import os
import requests

BASE_URL = "https://sportsbook-api2.p.rapidapi.com/v0"
RAPIDAPI_HOST = "sportsbook-api2.p.rapidapi.com"
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY") or os.getenv("SPORTSBOOK_RAPIDAPI_KEY")

HEADERS = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": RAPIDAPI_HOST
}

def get_events(sport: str):
    """
    Fetch events for a given league (NFL, NBA, etc.)
    Tries both ?league and ?category parameter conventions.
    """
    print(f"[DEBUG] get_events called for {sport}")

    possible_params = [
        {"league": sport},
        {"category": sport}
    ]

    for params in possible_params:
        url = f"{BASE_URL}/events"
        print(f"[DEBUG] Trying params: {params}")
        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
            print(f"[DEBUG] {url} -> {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                count = len(data.get("events", []))
                print(f"[DEBUG] Retrieved {count} events with {params}")
                if count > 0:
                    return data
            elif resp.status_code == 400:
                print(f"[WARN] Bad request for {params}")
        except Exception as e:
            print(f"[ERROR] get_events: {e}")

    return {"events": [], "error": "No valid event results found."}


def get_odds(sport: str):
    """
    Fetch odds for the same sport.
    """
    url = f"{BASE_URL}/odds"
    params = {"league": sport}
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
