# sports_agent.py
import traceback
from sportsbook_api import get_events, get_odds, get_props, get_advantages

def build_payload(
    sport_key: str,
    allow_api: bool = True,
    include_props: bool = True,
    include_advantages: bool = True,
    max_games: int = 10
):
    """
    Combine sportsbook API data into one clean payload.
    """
    print(f"[DEBUG] build_payload -> sport={sport_key}, allow_api={allow_api}")

    try:
        if not allow_api:
            return {"status": "stub", "events": [], "message": "API calls disabled"}

        # Step 1: Get events
        events_resp = get_events(sport_key)
        events = events_resp.get("data", {}).get("events", [])
        if not events:
            print(f"[WARN] No events found for {sport_key}")
            return {"status": "empty", "events": [], "source": events_resp.get("url")}

        limited_events = events[:max_games]
        results = []

        # Step 2: Enrich each event
        for e in limited_events:
            event_id = e.get("key") or e.get("id")
            enriched = {"event": e, "event_id": event_id}

            # Odds
            odds_resp = get_odds(event_id)
            enriched["odds"] = odds_resp.get("data")

            # Props (optional)
            if include_props:
                props_resp = get_props(event_id)
                enriched["props"] = props_resp.get("data")

            # Advantages (optional)
            if include_advantages:
                adv_resp = get_advantages(event_id)
                enriched["advantages"] = adv_resp.get("data")

            results.append(enriched)

        return {
            "status": "success",
            "sport": sport_key,
            "event_count": len(results),
            "events": results
        }

    except Exception:
        print("[ERROR] Exception in build_payload:")
        print(traceback.format_exc())
        return {"status": "error", "trace": traceback.format_exc()}
