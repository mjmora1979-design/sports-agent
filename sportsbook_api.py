import datetime
from sportsbook_api import (
    list_competitions,
    get_events_for_competition,
    get_events_by_keys,
    get_markets,
)

# Books we actually care about
SUPPORTED_BOOKS = {"draftkings", "fanduel"}


def find_competition_key(sport_hint: str):
    """
    Scan all competitions and return the first one whose name or key matches sport_hint (e.g. 'nfl').
    """
    competitions = list_competitions()
    if isinstance(competitions, dict) and "error" in competitions:
        return None

    for comp in competitions:
        name = (comp.get("name") or "").lower()
        key = (comp.get("competitionKey") or "").lower()
        if sport_hint.lower() in name or sport_hint.lower() in key:
            return comp.get("competitionKey")

    print(f"[WARN] No competitionKey found for {sport_hint}")
    return None


def build_payload(sport: str, allow_api: bool = True, max_games: int = 10):
    """
    Build JSON payload with competitions, events, and odds.
    """
    payload = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "sport": sport,
        "events": [],
        "markets": [],
    }

    if not allow_api:
        payload["note"] = "API disabled, stubbed data."
        return payload

    # 1️⃣ Find the right competition key (e.g. NFL)
    comp_key = find_competition_key(sport)
    if not comp_key:
        payload["error"] = "Competition not found"
        return payload
    payload["competitionKey"] = comp_key

    # 2️⃣ Pull all events for that competition
    events = get_events_for_competition(comp_key, event_type="MATCH")
    if isinstance(events, dict) and "error" in events:
        payload["events_error"] = events
        return payload

    if len(events) > max_games:
        events = events[:max_games]
    payload["events_raw_count"] = len(events)

    # Extract eventKeys
    event_keys = [e.get("eventKey") for e in events if e.get("eventKey")]
    if not event_keys:
        payload["error"] = "No eventKeys found"
        return payload

    # 3️⃣ Fetch details for those events
    detailed_events = get_events_by_keys(event_keys)
    payload["events"] = detailed_events.get("events", [])

    # 4️⃣ For each event, fetch markets (odds + props)
    combined_markets = []
    for ev in payload["events"]:
        ev_key = ev.get("eventKey")
        if not ev_key:
            continue
        markets_resp = get_markets(ev_key)
        markets = markets_resp.get("markets", []) if isinstance(markets_resp, dict) else []
        # Filter to supported books only
        filtered = []
        for m in markets:
            books = [b for b in m.get("books", []) if b.get("bookKey") in SUPPORTED_BOOKS]
            if books:
                m["books"] = books
                filtered.append(m)
        if filtered:
            combined_markets.append({"eventKey": ev_key, "markets": filtered})

    payload["markets"] = combined_markets
    payload["markets_count"] = len(combined_markets)
    payload["books"] = list(SUPPORTED_BOOKS)

    return payload
