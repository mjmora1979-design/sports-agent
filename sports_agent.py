"""
sports_agent.py
---------------
Core logic for building NFL odds payloads using The Odds API.

This version:
- Pulls data from odds_api_collector.py
- Cleans and structures results
- Ready for model analysis and ChatGPT integration
"""

import datetime
from odds_api_collector import get_or_fetch

def parse_odds(event):
    """
    Normalize a single event's odds into a simple dict.

    Args:
        event (dict): Raw event object from The Odds API.

    Returns:
        dict: Clean structure with basic line info.
    """
    game = {
        "id": event.get("id"),
        "commence_time": event.get("commence_time"),
        "home_team": event.get("home_team"),
        "away_team": event.get("away_team"),
        "bookmakers": [],
    }

    for site in event.get("bookmakers", []):
        # Only include DK and FD for simplicity
        if site["key"] not in ["draftkings", "fanduel"]:
            continue

        book = {
            "bookmaker": site["key"],
            "last_update": site.get("last_update"),
            "markets": {}
        }

        for market in site.get("markets", []):
            m_key = market["key"]
            outcomes = market.get("outcomes", [])
            book["markets"][m_key] = {}

            for outcome in outcomes:
                name = outcome["name"]
                price = outcome.get("price")
                point = outcome.get("point")
                book["markets"][m_key][name] = {
                    "price": price,
                    "point": point
                }

        game["bookmakers"].append(book)

    return game


def build_payload(sport="nfl", snapshot_type="opening"):
    """
    Build structured JSON payload of NFL odds for analysis.

    Args:
        sport (str): Sport identifier (currently only "nfl").
        snapshot_type (str): "opening" or "closing".

    Returns:
        dict: Payload ready for GPT/model consumption.
    """
    print(f"[INFO] Building payload for {sport.upper()} ({snapshot_type})")

    odds_data = get_or_fetch(snapshot_type)
    if not odds_data:
        return {"error": f"No odds data available for {snapshot_type}"}

    games = [parse_odds(event) for event in odds_data]

    payload = {
        "sport": sport,
        "snapshot_type": snapshot_type,
        "timestamp_utc": datetime.datetime.utcnow().isoformat(),
        "game_count": len(games),
        "games": games,
    }

    print(f"[INFO] Built payload with {len(games)} games.")
    return payload


if __name__ == "__main__":
    # Simple test
    data = build_payload("nfl", "opening")
    print(f"✅ Retrieved {data['game_count']} games.")
