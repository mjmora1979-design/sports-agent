import datetime
from sportsbook_api import get_events, get_odds

def build_payload(sport: str, allow_api: bool = True, max_games: int = 10):
    """
    Build JSON payload with events and odds.
    """
    print(f"[DEBUG] build_payload called with sport={sport}, allow_api={allow_api}")

    payload = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "sport": sport,
        "events": [],
        "odds": [],
    }

    if allow_api:
        print("[DEBUG] API mode enabled — fetching live data...")
        events_resp = get_events(sport)
        odds_resp = get_odds(sport)

        if isinstance(events_resp, dict):
            payload["events"] = events_resp.get("events", [])
            payload["events_count"] = len(payload["events"])
        else:
            payload["events_error"] = "Invalid event response"

        if isinstance(odds_resp, dict):
            payload["odds"] = odds_resp.get("odds", [])
            payload["odds_count"] = len(payload["odds"])
        else:
            payload["odds_error"] = "Invalid odds response"
    else:
        payload["note"] = "API disabled, returning stubbed data."

    print(f"[DEBUG] Final payload keys: {list(payload.keys())}")
    return payload
