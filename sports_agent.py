import datetime
from sportsbook_api import get_events, get_odds

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
        # Events (games)
        events_resp = get_events(sport)
        games = events_resp.get("events", [])
        print(f"[DEBUG] Retrieved {len(games)} events")

        # Odds
        odds_resp = get_odds(sport)
        odds = odds_resp.get("odds", [])
        print(f"[DEBUG] Retrieved {len(odds)} odds entries")

        # Trim if max_games is set
        if games and max_games:
            games = games[:max_games]
            print(f"[DEBUG] Trimmed games to {len(games)} entries (max_games={max_games})")
        if odds and max_games:
            odds = odds[:max_games]
            print(f"[DEBUG] Trimmed odds to {len(odds)} entries (max_games={max_games})")

    # Survivor mode (NFL only)
    survivor = {
        "used": [],
        "week": get_week(sport) if sport == "nfl" else None
    }

    return {
        "games": games,
        "odds": odds,
        "status": "success",
        "survivor": survivor,
        "week": survivor.get("week")
    }

def get_week(sport: str) -> int:
    """Derive the current week number for NFL or fallback to calendar week."""
    if sport != "nfl":
        return None
    try:
        # Rough fallback: ISO calendar week
        today = datetime.date.today()
        week_num = today.isocalendar()[1]
        print(f"[DEBUG] Fallback NFL week = {week_num}")
        return week_num
    except Exception as e:
        print(f"[ERROR] get_week failed: {e}")
        return 0
