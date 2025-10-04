import os
import requests
import datetime

# RapidAPI Sportsbook API2 configuration
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "sportsbook-api2.p.rapidapi.com")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")

# Default base paths to test
BASE_URLS = [
    "https://sportsbook-api2.p.rapidapi.com/v0",
    "https://sportsbook-api2.p.rapidapi.com/v1",
    "https://sportsbook-api2.p.rapidapi.com/api/v1"
]


def make_request(url: str, params: dict = None):
    """Generic request handler with RapidAPI headers and error logging."""
    headers = {
        "x-rapidapi-host": RAPIDAPI_HOST,
        "x-rapidapi-key": RAPIDAPI_KEY,
    }

    try:
        r = requests.get(url, headers=headers, params=params or {}, timeout=15)
        if r.status_code == 200:
            return r.json()
        else:
            print(f"[WARN] {url} returned {r.status_code}")
            return {"status": r.status_code, "url": url}
    except Exception as e:
        print(f"[ERROR] Request failed: {url} -> {e}")
        return {"error": str(e), "url": url}


def get_competitions(sport_key: str):
    """List competitions for a given sport."""
    results = []
    for base in BASE_URLS:
        url = f"{base}/sports/{sport_key}/competitions"
        resp = make_request(url)
        if resp and isinstance(resp, dict):
            results.append({
                "base": base,
                "status": resp.get("status", 200),
                "competitions": resp.get("competitions", [])
            })
    return results


def get_events(sport_key: str, competition_key: str = "Q63E-wddv-ddp4"):
    """Return all events for a given competition."""
    events = []
    for base in BASE_URLS:
        url = f"{base}/competitions/{competition_key}/events"
        resp = make_request(url, params={"eventType": "MATCH"})
        if resp and isinstance(resp, dict):
            if "events" in resp:
                print(f"[OK] {url} -> {len(resp['events'])} results")
                events.extend(resp["events"])
            else:
                print(f"[WARN] {url} returned no events")
    return events


def get_odds(competition_key: str = "Q63E-wddv-ddp4"):
    """Return odds for a competition."""
    odds_results = []
    for base in BASE_URLS:
        url = f"{base}/odds"
        params = {"competitionKeys": competition_key}
        resp = make_request(url, params=params)
        if resp and isinstance(resp, dict) and "odds" in resp:
            print(f"[OK] {url} -> {len(resp['odds'])} odds entries")
            odds_results.extend(resp["odds"])
        else:
            print(f"[WARN] {url} returned no odds data")
    return odds_results


def get_props(competition_key: str = "Q63E-wddv-ddp4"):
    """Return props for a competition."""
    props_results = []
    for base in BASE_URLS:
        url = f"{base}/props"
        params = {"competitionKeys": competition_key}
        resp = make_request(url, params=params)
        if resp and isinstance(resp, dict) and "props" in resp:
            print(f"[OK] {url} -> {len(resp['props'])} props entries")
            props_results.extend(resp["props"])
        else:
            print(f"[WARN] {url} returned no props data")
    return props_results


def get_advantages(competition_key: str = "Q63E-wddv-ddp4"):
    """Return advantages for a competition."""
    adv_results = []
    for base in BASE_URLS:
        url = f"{base}/advantages"
        params = {"competitionKeys": competition_key}
        resp = make_request(url, params=params)
        if resp and isinstance(resp, dict) and "advantages" in resp:
            print(f"[OK] {url} -> {len(resp['advantages'])} advantage entries")
            adv_results.extend(resp["advantages"])
        else:
            print(f"[WARN] {url} returned no advantages data")
    return adv_results
