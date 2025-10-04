# sportsbook_api.py
import os
import requests
import traceback

# Load credentials from environment variables
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "sportsbook-api2.p.rapidapi.com")

BASE_URLS = [
    "https://sportsbook-api2.p.rapidapi.com/v0",
    "https://sportsbook-api2.p.rapidapi.com/v1",
    "https://sportsbook-api2.p.rapidapi.com/api/v1"
]

HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY or "",
    "x-rapidapi-host": RAPIDAPI_HOST
}


def _try_request(url, params=None):
    """Try multiple base paths until one works."""
    for base in BASE_URLS:
        full_url = f"{base}/{url.lstrip('/')}"
        try:
            resp = requests.get(full_url, headers=HEADERS, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                count = len(data) if isinstance(data, list) else len(data.get("events", []))
                print(f"[OK] {full_url} -> {count} results")
                return {"url": full_url, "count": count, "data": data}
            else:
                print(f"[WARN] {full_url} returned {resp.status_code}")
        except Exception:
            print(f"[ERROR] {traceback.format_exc()}")
    return {"url": None, "count": 0, "data": None}


def get_events(sport_key: str):
    """Fetch live or upcoming events for a sport."""
    # Known competition mappings (for now just NFL, NCAAF, NBA)
    competition_map = {
        "nfl": "Q63E-wddv-ddp4",
        "americanfootball_nfl": "Q63E-wddv-ddp4",
        "ncaaf": "x32N-pdNq-V9vM",
        "americanfootball_ncaaf": "x32N-pdNq-V9vM",
        "nba": "xla2-r0r0-7ypu"
    }

    comp_id = competition_map.get(sport_key.lower(), None)
    if not comp_id:
        return {"status": "error", "error": f"Unknown sport key {sport_key}"}

    url = f"competitions/{comp_id}/events"
    return _try_request(url, params={"eventType": "MATCH"})


def get_odds(event_id: str):
    """Fetch odds for a specific event."""
    url = f"events/{event_id}/odds"
    return _try_request(url)


def get_props(event_id: str):
    """Fetch player or team props for an event."""
    url = f"events/{event_id}/props"
    return _try_request(url)


def get_advantages(event_id: str):
    """Fetch sportsbook ‘advantages’ (where lines differ) for an event."""
    url = f"events/{event_id}/advantages"
    return _try_request(url)
