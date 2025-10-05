import os, requests

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = "sportsbook-api2.p.rapidapi.com"

HEADERS = {
    "x-rapidapi-host": RAPIDAPI_HOST,
    "x-rapidapi-key": RAPIDAPI_KEY
}

def get_events(sport="nfl"):
    """
    Fetches current events from sportsbook API (v0 competition instance)
    """
    url = "https://sportsbook-api2.p.rapidapi.com/v0/competitions/Q63E-wddv-ddp4/events?eventType=MATCH"
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        data = response.json()
        if "events" not in data:
            return {"events": [], "status": "no_events"}
        return {"events": data["events"], "status": "success"}
    except Exception as e:
        print(f"[ERROR] get_events failed: {e}")
        return {"events": [], "status": "error"}
