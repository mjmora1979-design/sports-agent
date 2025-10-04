import datetime
from sportsbook_api import (
    get_events,
    get_odds,
    get_props,
    get_advantages
)

def build_payload(
    sport: str,
    allow_api: bool = True,
    include_props: bool = True,
    include_adv: bool = True,
    max_games: int = 10
):
    """
    Build the JSON payload with events, odds, props, and advantages.

    Args:
        sport (str): The sport key ("nfl", "nba", etc.)
        allow_api (bool): Whether to call the API
        include_props (bool): Whether to pull props
        include_adv (bool): Whether to pull advantages
        max_games (int): Max number of games for quick testing
    """
    print(f"[DEBUG] build_payload -> sport={sport}, allow_api={allow_api}")

    data = {
        "sport": sport,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "status": "success",
        "events": [],
        "odds": [],
        "props": [],
        "advantages": []
    }

    if not allow_api:
        data["status"] = "stub"
        return data

    # NFL competition key (can expand logic later)
    competition_key = "Q63E-wddv-ddp4" if sport.lower() == "nfl" else None

    # 1️⃣ Events
    events = get_events(sport, competition_key)
    data["events"] = events[:max_games] if events else []

    # 2️⃣ Odds
    odds = get_odds(competition_key)
    data["odds"] = odds

    # 3️⃣ Props
    if include_props:
        props = get_props(competition_key)
        data["props"] = props

    # 4️⃣ Advantages
    if include_adv:
        adv = get_advantages(competition_key)
        data["advantages"] = adv

    data["event_count"] = len(data["events"])
    print(f"[DEBUG] build_payload complete with {data['event_count']} events")
    return data
