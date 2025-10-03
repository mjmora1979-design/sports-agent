import os
import requests
import datetime
from functools import lru_cache

# -------------------------
# Config
# -------------------------

API_KEY = os.getenv("SPORTSBOOK_RAPIDAPI_KEY")
API_HOST = os.getenv("SPORTSBOOK_RAPIDAPI_HOST")

BOOKS_DEFAULT = os.getenv("BOOKS_DEFAULT", "draftkings,fanduel").split(",")
CACHE_TTL = int(os.getenv("CACHE_TTL_SEC", "7200"))  # 2 hours


# -------------------------
# Internal cache
# -------------------------

def _make_cache_key(sport, start, end, books):
    return f"{sport}:{start}:{end}:{','.join(sorted(books))}"


_cache = {}


# -------------------------
# API Calls
# -------------------------

def get_odds_for_sport(sport, start, end, books=None):
    """
    Fetch odds for a sport from RapidAPI.
    Caches for CACHE_TTL seconds to stay under limits.
    """
    if books is None:
        books = BOOKS_DEFAULT

    cache_key = _make_cache_key(sport, start, end, books)
    now = datetime.datetime.utcnow().timestamp()

    # Check cache
    if cache_key in _cache:
        ts, data = _cache[cache_key]
        if now - ts < CACHE_TTL:
            return data

    url = f"https://{API_HOST}/odds"
    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": API_HOST
    }
    params = {
        "sport": sport,
        "region": "us",
        "mkt": "h2h,spreads,totals,player_props",
        "oddsFormat": "american"
    }

    # Debug logging (safe: we do not print your API key)
    print(f"[DEBUG] Requesting odds from: {url}")
    print(f"[DEBUG] Params: {params}")
    print(f"[DEBUG] Headers (no key): {{'X-RapidAPI-Host': '{API_HOST}'}}")

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        print(f"[DEBUG] Response status: {resp.status_code}")
        if resp.status_code != 200:
            print(f"[DEBUG] Response text: {resp.text[:300]}")
            return []
        data = resp.json()
    except Exception as e:
        print(f"[ERROR] Odds request failed: {e}")
        return []

    # Filter to requested books only
    filtered = []
    for ev in data.get("events", []):
        game_books = {}
        for b in ev.get("books", []):
            if b["book_key"] in books:
                game_books[b["book_key"]] = b
        if game_books:
            ev["books"] = game_books
            filtered.append(ev)

    # Cache result
    _cache[cache_key] = (now, filtered)
    return filtered
