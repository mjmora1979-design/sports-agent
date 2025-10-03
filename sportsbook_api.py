# sportsbook_api.py
# Wrapper for Sportsbook API (RapidAPI) with retries + 2h TTL cache.

import os, time, logging, requests
from typing import Dict, Any, List, Optional, Tuple
from requests.adapters import HTTPAdapter, Retry

# -------- ENV --------
RAPIDAPI_KEY  = os.getenv("SPORTSBOOK_RAPIDAPI_KEY", "")
RAPIDAPI_HOST = os.getenv("SPORTSBOOK_RAPIDAPI_HOST", "sportsbook-api2.p.rapidapi.com")
BOOKS_DEFAULT = os.getenv("BOOKS_DEFAULT", "draftkings,fanduel")
CACHE_TTL_SEC = int(os.getenv("CACHE_TTL_SEC", "7200"))

# -------- HTTP session with retries --------
def _session() -> requests.Session:
    s = requests.Session()
    retries = Retry(total=4, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.headers.update({
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST,
        "Accept": "application/json",
    })
    return s

_http = _session()

# -------- Simple TTL cache --------
_cache: Dict[str, Tuple[float, Any]] = {}

def _cache_get(key: str):
    now = time.time()
    v = _cache.get(key)
    if not v: return None
    ts, data = v
    if now - ts > CACHE_TTL_SEC:
        _cache.pop(key, None)
        return None
    return data

def _cache_set(key: str, data: Any):
    _cache[key] = (time.time(), data)

# ---- Map sports + props ----
COMP_KEYS = {
    "nfl":   "NFL",
    "ncaaf": "NCAAF",
    "nba":   "NBA",
    "mlb":   "MLB",
    "ncaab": "NCAAM",
}

PROP_MARKET_MAP = {
    "player_pass_yds":       "passing_yds",
    "player_rush_yds":       "rushing_yds",
    "player_receiving_yds":  "receiving_yds",
    "player_anytime_td":     "anytime_td",
    "player_pass_tds":       "pass_tds",
}

PRIMARY_MARKETS = ["moneyline", "spreads", "totals"]

def _normalize_book_name(name: str) -> str:
    n = (name or "").strip().lower()
    if "draft" in n: return "DraftKings"
    if "fan" in n:   return "FanDuel"
    return name or ""

def _build_cache_key(sport: str, scope: str, books: str, markets: List[str], start_iso: str, end_iso: str):
    mk = ",".join(sorted(markets))
    return f"sportsbookapi|{sport}|{scope}|{books}|{mk}|{start_iso}|{end_iso}"

def get_events_with_odds(
    sport: str,
    start_iso: str,
    end_iso: str,
    include_props: bool,
    wanted_prop_keys: List[str],
    wanted_books: List[str],
    odds_format: str = "american",
) -> Dict[str, Any]:
    """Fetch events + odds from Sportsbook API. 
       Uses cache. Filters to DK/FD client-side if server sends more."""
    
    prop_market_ids = [PROP_MARKET_MAP[k] for k in wanted_prop_keys if k in PROP_MARKET_MAP]
    all_markets = PRIMARY_MARKETS + (prop_market_ids if include_props else [])
    books_param = ",".join(wanted_books) if wanted_books else BOOKS_DEFAULT

    cache_key = _build_cache_key(sport, "range", books_param, all_markets, start_iso, end_iso)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    # Candidate API endpoints (depends on plan, update if Swagger shows different path)
    candidate_paths = [
        (f"/v0/competitions/{COMP_KEYS.get(sport, sport)}/events",
         {
             "startDate": start_iso,
             "endDate":   end_iso,
             "books":     books_param,
             "markets":   ",".join(all_markets),
             "oddsFormat": odds_format
         }),
        ("/v0/events",
         {
             "sport": sport,
             "startDate": start_iso,
             "endDate":   end_iso,
             "books":     books_param,
             "markets":   ",".join(all_markets),
             "oddsFormat": odds_format
         }),
    ]

    resp_json, last_err = None, None
    for path, params in candidate_paths:
        try:
            r = _http.get(f"https://{RAPIDAPI_HOST}{path}", params={k:v for k,v in params.items() if v})
            if r.status_code == 200:
                resp_json = r.json()
                break
            else:
                last_err = f"{r.status_code} {r.text[:200]}"
        except Exception as e:
            last_err = str(e)

    if resp_json is None:
        logging.warning(f"Sportsbook API: failed events fetch; last_err={last_err}")
        resp_json = {"events": []}

    # Normalize books
    for ev in resp_json.get("events", []):
        books = ev.get("books", [])
        ev["books"] = [b for b in books if _normalize_book_name(b.get("name","")) in ("DraftKings","FanDuel")]

    _cache_set(cache_key, resp_json)
    return resp_json
