import datetime
from sportsbook_api import get_events, get_odds

_cache = {}

def _cached(key):
    val = _cache.get(key)
    if val and (datetime.datetime.utcnow() - val["ts"]).seconds < 900:
        print(f"[DEBUG] Using cached data for {key}")
        return val["data"]

def _store(key, data):
    _cache[key] = {"ts": datetime.datetime.utcnow(), "data": data}

def get_week(sport: str):
    if sport != "nfl":
        return None
    today = datetime.date.today()
    week_num = today.isocalendar()[1] - 35
    return max(1, min(18, week_num))

def build_payload(sport: str, allow_api: bool = True, max_games: int = 10):
    print(f"[DEBUG] build_payload called with sport={sport}, allow_api={allow_api}")
    cache_key = f"{sport}_{allow_api}_{max_games}"
    cached = _cached(cache_key)
    if cached:
        return cached

    games, odds = [], []
    if allow_api:
        events_resp = get_events(sport)
        if events_resp.get("status") == "success":
            games = events_resp.get("data", [])[:max_games]

        odds_resp = get_odds(sport)
        if odds_resp.get("status") == "success":
            odds = odds_resp.get("data", [])[:max_games]

    survivor = {"used": [], "week": get_week(sport) if sport == "nfl" else None}

    payload = {
        "status": "success" if games or odds else "error",
        "source": "sports-agent",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "sport": sport,
        "summary": {
            "games_count": len(games),
            "odds_count": len(odds),
            "week": survivor.get("week"),
        },
        "data": {"games": games, "odds": odds, "survivor": survivor},
    }

    _store(cache_key, payload)
    return payload
