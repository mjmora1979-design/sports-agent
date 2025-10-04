import os
import requests
import datetime

# Pull environment variables - FIXED NAMES
API_HOST = os.environ.get("RAPIDAPI_HOST", "sportsbook-api2.p.rapidapi.com")
API_KEY = os.environ.get("RAPIDAPI_KEY")

# Headers for RapidAPI - FIXED CAPITALIZATION
HEADERS = {
    "X-RapidAPI-Host": API_HOST,
    "X-RapidAPI-Key": API_KEY,
    "accept": "application/json"
}

def _debug_headers():
    """Print key debug info without exposing full secrets."""
    print(f"[DEBUG] Host = {HEADERS.get('X-RapidAPI-Host')}")
    print(f"[DEBUG] API key present? {bool(HEADERS.get('X-RapidAPI-Key'))}")

def get_events(sport: str, region: str = "us", days: int = 7):
    """Fetch events (games) for a sport."""
    _debug_headers()
    try:
        # Map common sport names to API format
        sport_map = {
            "nfl": "americanfootball_nfl",
            "ncaaf": "americanfootball_ncaaf",
            "nba": "basketball_nba",
            "ncaab": "basketball_ncaab",
            "mlb": "baseball_mlb",
            "nhl": "icehockey_nhl"
        }
        
        api_sport = sport_map.get(sport.lower(), sport)
        
        # FIXED: Changed to /v0/events/ (from your RapidAPI screenshot)
        url = f"https://{API_HOST}/v0/events/"
        
        params = {
            "sport": api_sport
        }
        
        print(f"[DEBUG] Requesting events from: {url}")
        print(f"[DEBUG] Params: {params}")
        
        res = requests.get(url, headers=HEADERS, params=params, timeout=15)
        
        print(f"[DEBUG] Response status: {res.status_code}")
        
        res.raise_for_status()
        data = res.json()
        
        print(f"[DEBUG] Retrieved {len(data.get('events', []))} events")
        
        return data
        
    except requests.exceptions.HTTPError as e:
        print(f"[ERROR] HTTP {e.response.status_code}: {e.response.text[:300]}")
        return {"events": []}
    except Exception as e:
        print(f"[ERROR] get_events failed: {e}")
        return {"events": []}

def get_odds(sport: str, region: str = "us", markets: str = "h2h,spreads,totals,player_props"):
    """Fetch odds for a sport."""
    _debug_headers()
    try:
        sport_map = {
            "nfl": "americanfootball_nfl",
            "ncaaf": "americanfootball_ncaaf",
            "nba": "basketball_nba",
            "ncaab": "basketball_ncaab",
            "mlb": "baseball_mlb",
            "nhl": "icehockey_nhl"
        }
        
        api_sport = sport_map.get(sport.lower(), sport)
        
        # FIXED: Changed to /v0/odds/ (assuming same pattern as events)
        url = f"https://{API_HOST}/v0/odds/"
        
        params = {
            "sport": api_sport,
            "markets": markets,
            "oddsFormat": "american"
        }
        
        print(f"[DEBUG] Requesting odds from: {url}")
        print(f"[DEBUG] Params: {params}")
        
        res = requests.get(url, headers=HEADERS, params=params, timeout=15)
        
        print(f"[DEBUG] Response status: {res.status_code}")
        
        res.raise_for_status()
        data = res.json()
        
        print(f"[DEBUG] Retrieved odds data")
        
        return data
        
    except requests.exceptions.HTTPError as e:
        print(f"[ERROR] HTTP {e.response.status_code}: {e.response.text[:300]}")
        return {"odds": []}
    except Exception as e:
        print(f"[ERROR] get_odds failed: {e}")
        return {"odds": []}
