import os
import requests
import traceback

RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "sportsbook-api2.p.rapidapi.com")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
HEADERS = {
    "x-rapidapi-host": RAPIDAPI_HOST,
    "x-rapidapi-key": RAPIDAPI_KEY
}

def get_events(sport="nfl"):
    """
    Fetch competition events + markets (odds) for the given sport.
    """
    # For now, we assume NFL competitionKey
    url = f"https://{RAPIDAPI_HOST}/v0/competitions/Q63E-wddv-ddp4/events?eventType=MATCH"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        data = resp.json()
        return data
    except Exception:
        print("[ERROR] get_events:", traceback.format_exc())
        return {"events": []}
