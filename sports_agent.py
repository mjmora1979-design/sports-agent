import datetime
from sportsbook_api import (
    list_competitions,
    get_events_for_competition,
    get_markets
)

def build_payload(
    sport: str,
    allow_api: bool = True,
    max_games: int = 10
):
    """
    Build the JSON payload with games and odds.

    Args:
        sport (str): The sport key ("nfl", "nba", "ncaaf", etc.)
        allow_api (bool): Whether to call the API (True) or return stub.
        max_games (int): Limit number of games returned (for testing).
    """
    print(f"[DEBUG] build_payload called with sport={sport}, allow_api={allow_api}, max_games={max_games}")

    games, odds = [], []

    if allow_api:
        try:
            # Step 1: Get competitions and find the matching sport
            comps = list_competitions()
            if isinstance(comps, dict) and "error" in comps:
                return {"error": comps["error"]}

            sport_comp = None
            for c in comps:
                if sport.lower() in str(c.get("name", "")).lower():
                    sport_comp = c
                    break

            if not sport_comp:
                return {"error": f"No competition found for sport '{sport}'"}

            comp_key = sport_comp.get("competitionKey")
            print(f"[DEBUG] Found competition key for {sport}: {comp_key}")

            # Step 2: Get events for this competition
            events = get_events_for_competition(comp_key, event_type="MATCH")
            if isinstance(events, dict) and "error" in events:
                return {"error": events["error"]}

            games = events[:max_games]
            print(f"[DEBUG] Retrieved {len(games)} games for {sport}")

            # Step 3: Pull odds (markets) for each game
            for g in games:
                ekey = g.get("eventKey")
                if not ekey:
                    continue
                mdata = get_markets(ekey)
                odds.append({
                    "eventKey": ekey,
                    "markets": mdata
                })

        except Exception as e:
            print("[ERROR] build_payload failed:", e)
            return {"error": str(e)}

    else:
        # Offline stub
        games = [{"event": "Stub Game 1"}, {"event": "Stub Game 2"}]
        odds = [{"eventKey": "stub", "odds": "N/A"}]

    payload = {
        "timestamp": datetime.datetime.now().isoformat(),
        "sport": sport,
        "games": games,
        "odds": odds
    }

    print("[DEBUG] build_payload completed successfully")
    return payload
