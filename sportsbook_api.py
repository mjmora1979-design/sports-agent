import os, requests, datetime, json, hashlib

RAPIDAPI_HOST = os.getenv("SPORTSBOOK_RAPIDAPI_HOST", "sportsbook-api2.p.rapidapi.com")
RAPIDAPI_KEY = os.getenv("SPORTSBOOK_RAPIDAPI_KEY")

BASE_URL = f"https://{RAPIDAPI_HOST}"
CACHE_TTL_SEC = int(os.getenv("CACHE_TTL_SEC", "7200"))  # default 2 hours
CACHE_DIR = "/tmp/sports_cache"

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def get_headers():
    return {
        "X-RapidAPI-Host": RAPIDAPI_HOST,
        "X-RapidAPI-Key": RAPIDAPI_KEY
    }

def _cache_path(key: str) -> str:
    hashed = hashlib.md5(key.encode()).hexdigest()
    return os.path.join(CACHE_DIR, f"{hashed}.json")

def _read_cache(key: str):
    path = _cache_path(key)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            cached = json.load(f)
        if datetime.datetime.utcnow().timestamp() - cached["timestamp"] < CACHE_TTL_SEC:
            return cached["data"]
    except Exception:
        return None
    return None

def _write_cache(key: str, data):
    path = _cache_path(key)
    try:
        with open(path, "w") as f:
            json.dump({"timestamp": datetime.datetime.utcnow().timestamp(), "data": data}, f)
    except Exception as e:
        print(f"[WARN] Cache write failed: {e}")

def get_odds(sport, from_date=None, to_date=None, force_direct=False):
    """
    Pull odds with cache.
    Only 1 API hit per sport/day unless force_direct=True bypasses cache.
    """
    cache_key = f"odds:{sport}:{datetime.date.today().isoformat()}"
    if not force_direct:
        cached = _read_cache(cache_key)
        if cached:
            print(f"[CACHE] Using cached odds for {sport}")
            return cached

    url = f"{BASE_URL}/odds"
    params = {
        "sport": sport,
        "region": "us",
        "mkt": "h2h,spreads,totals,player_props",
        "oddsFormat": "american"
    }

    try:
        print(f"[DEBUG] Requesting odds from {url} (force_direct={force_direct})")
        resp = requests.get(url, headers=get_headers(), params=params, timeout=20)
        resp.raise_for_status()
        events = resp.json().get("events", [])
        _write_cache(cache_key, events)
        return events
    except Exception as e:
        print(f"[ERROR] get_odds: {e}")
        return []
