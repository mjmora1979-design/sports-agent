import os
import requests
import datetime
from functools import lru_cache

# -------------------------
# Config
# -------------------------
RAPIDAPI_HOST = os.getenv("SPORTSBOOK_RAPIDAPI_HOST", "sportsbook-api2.p.rapidapi.com")
RAPIDAPI_KEY = os.getenv("SPORTSBOOK_RAPIDAPI_KEY")

BASE_URL = f"https://{RAPIDAPI_HOST}"

HEADERS = {
    "X-RapidAPI-Host": RAPIDAPI_HOST,
    "X-RapidAPI-Key": RAPIDAPI_KEY
}

CACHE_TTL = int(os.getenv("CACHE_TTL_SEC", "7200"))  # default 2 hours


# -------------------------
# API Calls
# -------------------------

@lru_cache(maxsize=32)
def get_events(sport: str):
    """
    Get events (games) for a given sport.
    Example endpoint: /events/nfl
    """
    url = f"{BASE_URL}/events/{sport}"
    print(f"[DEBUG] GET {url}")
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    return resp.json().get("events", [])


@lru_cache(maxsize=128)
def get_markets(event_id: str):
    """
    Get all markets for a specific event.
    Example endpoint: /markets/{event_id}
    """
    url = f"{BASE_URL}/markets/{event_id}"
    print(f"[DEBUG] GET {url}")
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    return resp.json().get("markets", {})


def get_odds(sport: str, max_games: int = None):
    """
    Get odds + props for all events in a sport.
    """
    try:
        events = get_events(sport)
    except Exception as e:
        print(f"[ERROR] get_events failed: {e}")
        return []

    games = []
    count = 0

    for ev in events:
        if max_games and count >= max_games:
            break

        event_id = ev.get("id")
        home = ev.get("home_team")
        away = ev.get("away_team")
        commence = ev.get("commence_time")

        try:
            markets = get_markets(event_id)
        except Exception as e:
            print(f"[ERROR] get_markets failed for {event_id}: {e}")
            continue

        games.append({
            "id": event_id,
            "home_team": home,
            "away_team": away,
            "commence_time": commence,
            "books": markets  # Already structured by API
        })
        count += 1

    return games
