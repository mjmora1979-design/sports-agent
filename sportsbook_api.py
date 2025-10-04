import os, requests, datetime

API_HOST = os.environ.get("RAPIDAPI_HOST", "sportsbook-api2.p.rapidapi.com")
API_KEY  = os.environ.get("RAPIDAPI_KEY")
BASE_URL = f"https://{API_HOST}/v0"

HEADERS = {
    "X-RapidAPI-Host": API_HOST,
    "X-RapidAPI-Key": API_KEY,
    "accept": "application/json",
}

def get_events(sport: str):
    sport_map = {
        "nfl": "americanfootball_nfl",
        "ncaaf": "americanfootball_ncaaf",
        "nba": "basketball_nba",
        "ncaab": "basketball_ncaab",
        "mlb": "baseball_mlb",
        "nhl": "icehockey_nhl",
    }
    api_sport = sport_map.get(sport.lower(), sport)
    url = f"{BASE_URL}/events/"
    try:
        res = requests.get(url, headers=HEADERS, params={"sport": api_sport}, timeout=15)
        data = res.json() if res.ok else {}
        return {
            "status": "success" if res.ok else "error",
            "endpoint": "events",
            "sport": sport,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "count": len(data.get("events", [])) if isinstance(data, dict) else 0,
            "data": data.get("events", []),
        }
    except Exception as e:
        return {"status": "error", "endpoint": "events", "sport": sport, "message": str(e)}

def get_odds(sport: str, markets: str = "h2h,spreads,totals,player_props"):
    sport_map = {
        "nfl": "americanfootball_nfl",
        "ncaaf": "americanfootball_ncaaf",
        "nba": "basketball_nba",
        "ncaab": "basketball_ncaab",
        "mlb": "baseball_mlb",
        "nhl": "icehockey_nhl",
    }
    api_sport = sport_map.get(sport.lower(), sport)
    url = f"{BASE_URL}/odds/"
    try:
        res = requests.get(
            url,
            headers=HEADERS,
            params={"sport": api_sport, "markets": markets, "oddsFormat": "american"},
            timeout=15,
        )
        data = res.json() if res.ok else {}
        return {
            "status": "success" if res.ok else "error",
            "endpoint": "odds",
            "sport": sport,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "count": len(data.get("odds", [])) if isinstance(data, dict) else 0,
            "data": data.get("odds", []),
        }
    except Exception as e:
        return {"status": "error", "endpoint": "odds", "sport": sport, "message": str(e)}
