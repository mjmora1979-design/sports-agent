# sports_agent.py
# Builds payloads using sportsbook_api for sports data, odds, and props

import datetime
from sportsbook_api import (
    get_competitions,
    get_events,
    get_event_details,
    get_event_markets,
    get_advantages,
)

# -------------------------------------------------------------
# Build the unified payload
# -------------------------------------------------------------
def build_payload(
    sport_key: str,
    allow_api: bool = True,
    include_props: bool = True,
    include_advantages: bool = True,
    max_games: int = 10
):
    """
    Build a complete JSON payload with games, odds, props, and insights.

    Args:
        sport_key (str): Competition key or shorthand (e.g., "nfl", "nba", etc.)
        allow_api (bool): Whether to actually call the API
        include_props (bool): Include player/market props in payload
        include_advantages (bool): Include advantages API insights
        max_games (int): Limit for test mode
    """
    print(f"[DEBUG] build_payload called with sport_key={sport_key}, allow_api={allow_api}")

    payload = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "sport": sport_key,
        "events": [],
        "markets": [],
        "advantages": [],
    }

    if not allow_api:
        print("[DEBUG] API disabled; returning stub payload.")
        return payload

    # ---------------------------------------------------------
    # 1️⃣ Fetch competition key
    # ---------------------------------------------------------
    competitions_resp = get_competitions()
    comp_list = competitions_resp.get("competitions", []) if isinstance(competitions_resp, dict) else []
    target_competition = None

    for comp in comp_list:
        if sport_key.lower() in comp.get("key", "").lower() or sport_key.lower() in comp.get("name", "").lower():
            target_competition = comp.get("key")
            break

    if not target_competition:
        print(f"[WARN] Could not match sport_key={sport_key} to a competition. Using default NFL key.")
        target_competition = "Q63E-wddv-ddp4"  # NFL default from API examples

    # ---------------------------------------------------------
    # 2️⃣ Fetch events
    # ---------------------------------------------------------
    print(f"[DEBUG] Fetching events for competition {target_competition}...")
    events_resp = get_events(target_competition)
    events = events_resp.get("events", []) if isinstance(events_resp, dict) else []

    if not events:
        print(f"[WARN] No events found for {sport_key}")
        return payload

    events = events[:max_games]
    payload["events"] = events

    # ---------------------------------------------------------
    # 3️⃣ Fetch markets & props for each event
    # ---------------------------------------------------------
    print(f"[DEBUG] Fetching markets for up to {len(events)} events...")
    for event in events:
        event_key = event.get("key")
        if not event_key:
            continue

        details = get_event_details(event_key)
        markets = get_event_markets(event_key) if include_props else {}

        payload["markets"].append({
            "event_key": event_key,
            "details": details,
            "markets": markets
        })

    # ---------------------------------------------------------
    # 4️⃣ Fetch advantages (optional insights)
    # ---------------------------------------------------------
    if include_advantages:
        print("[DEBUG] Fetching advantages...")
        adv_data = get_advantages()
        payload["advantages"] = adv_data

    # ---------------------------------------------------------
    # 5️⃣ Return structured payload
    # ---------------------------------------------------------
    print(f"[DEBUG] Payload built successfully with {len(payload['events'])} events.")
    return payload


# -------------------------------------------------------------
# 6️⃣ Debug mode
# -------------------------------------------------------------
if __name__ == "__main__":
    print("[DEBUG] Starting sports_agent.py self-test...")
    data = build_payload("nfl", allow_api=True, include_props=True, include_advantages=True, max_games=3)
    import json
    print(json.dumps(data, indent=2))
