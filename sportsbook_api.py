import os
import requests
import datetime

API_HOST = os.getenv("SPORTSBOOK_RAPIDAPI_HOST", "sportsbook-api2.p.rapidapi.com")
API_KEY = os.getenv("SPORTSBOOK_RAPIDAPI_KEY", "")  # must be set in Render
BOOKS_DEFAULT = os.getenv("BOOKS_DEFAULT", "draftkings,fanduel")

BASE_URL = f"https://{API_HOST}/v1"

def _headers():
    if API_KEY:
        return {
            "X-RapidAPI-Key": API_KEY,
            "X-RapidAPI-Host": API_HOST,
        }
    return {"X-RapidAPI-Host": API_HOST}

def get_events(sport: str, region: str = "us"):
    """Fetch upcoming events for given sport (IDs, teams, commence_time)."""
    url = f"{BASE_URL}/events"
    params = {"sport": sport, "region": region}
    try:
        r = requests.get(url, headers=_headers(), params=params, timeout=15)
        r.raise_for_status()
        return r.json().get("events", [])
    except Exception as e:
        print("[ERROR] get_events failed:", e)
        return []

def get_odds(event_id: str, books: str = BOOKS_DEFAULT):
    """Fetch odds (h2h, spreads, totals) for a specific event."""
    url = f"{BASE_URL}/odds"
    params = {"event_id": event_id, "books": books, "mkt": "h2h,spreads,totals"}
    try:
        r = requests.get(url, headers=_headers(), params=params, timeout=15)
        r.raise_for_status()
        return r.json().get("odds", {})
    except Exception as e:
        print("[ERROR] get_odds failed:", e)
        return {}

def get_props(event_id: str, books: str = BOOKS_DEFAULT):
    """Fetch props (player markets) for a specific event."""
    url = f"{BASE_URL}/props"
    params = {"event_id": event_id, "books": books}
    try:
        r = requests.get(url, headers=_headers(), params=params, timeout=15)
        r.raise_for_status()
        return r.json().get("props", {})
    except Exception as e:
        print("[ERROR] get_props failed:", e)
        return {}

def fetch_odds_and_props(sport: str, start: str = None, end: str = None):
    """
    Double-pull:
      1. Get events (ids, teams, times).
      2. For each event → odds + props.
      3. Merge into normalized dict.
    """
    events = get_events(sport)
    results = []

    for ev in events:
        event_id = ev.get("id")
        home = ev.get("home_team")
        away = ev.get("away_team")
        commence = ev.get("commence_time")

        odds = get_odds(event_id)
        props = get_props(event_id)

        merged = {
            "id": event_id,
            "home_team": home,
            "away_team": away,
            "commence_time": commence,
            "books": {}
        }

        # Normalize books
        for book, data in odds.items():
            book_name = "DraftKings" if "draftkings" in book.lower() else \
                        "FanDuel" if "fanduel" in book.lower() else book
            merged["books"][book_name] = {
                "h2h": data.get("h2h", {}),
                "spreads": data.get("spreads", []),
                "totals": data.get("totals", {}),
                "props": props.get(book, {})  # merge props if present
            }

        results.append(merged)

    return results
