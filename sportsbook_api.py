import os
import requests

API_HOST = os.getenv("RAPIDAPI_HOST", "sportsbook-api2.p.rapidapi.com")
API_KEY = os.getenv("RAPIDAPI_KEY")

BASE_URL = f"https://{API_HOST}/v0"

HEADERS = {
    "X-RapidAPI-Host": API_HOST,
    "X-RapidAPI-Key": API_KEY,
    "accept": "application/json"
}


def _debug_headers():
    print(f"[DEBUG] Host = {HEADERS.get('X-RapidAPI-Host')}")
    print(f"[DEBUG] API key present? {bool(HEADERS.get('X-RapidAPI-Key'))}")


def get_events(event_keys=None, return_type="array"):
    """
    Fetch events from the Sportsbook API.
    Optionally accepts a list of event keys for direct lookups.
    """
    _debug_headers()
    try:
        url = f"{BASE_URL}/events/"
        params = {"returnType": return_type}
        if event_keys:
            params["eventKeys"] = event_keys

        print(f"[DEBUG] Requesting events: {url}")
        print(f"[DEBUG] Params: {params}")

        res = requests.get(url, headers=HEADERS, params=params, timeout=15)
        print(f"[DEBUG] Response status: {res.status_code}")

        res.raise_for_status()
        data = res.json()

        events = data.get("events", [])
        print(f"[DEBUG] Retrieved {len(events)} events")

        return {"events": events}

    except requests.exceptions.HTTPError as e:
        print(f"[ERROR] HTTP {e.response.status_code}: {e.response.text[:300]}")
        return {"events": []}
    except Exception as e:
        print(f"[ERROR] get_events failed: {e}")
        return {"events": []}


def get_odds(event_keys=None, return_type="array"):
    """
    Fetch odds for specific event keys (if available).
    """
    _debug_headers()
    try:
        url = f"{BASE_URL}/odds/"
        params = {"returnType": return_type}
        if event_keys:
            params["eventKeys"] = event_keys

        print(f"[DEBUG] Requesting odds: {url}")
        print(f"[DEBUG] Params: {params}")

        res = requests.get(url, headers=HEADERS, params=params, timeout=15)
        print(f"[DEBUG] Response status: {res.status_code}")

        res.raise_for_status()
        data = res.json()
        odds = data.get("odds", [])

        print(f"[DEBUG] Retrieved {len(odds)} odds entries")
        return {"odds": odds}

    except requests.exceptions.HTTPError as e:
        print(f"[ERROR] HTTP {e.response.status_code}: {e.response.text[:300]}")
        return {"odds": []}
    except Exception as e:
        print(f"[ERROR] get_odds failed: {e}")
        return {"odds": []}
