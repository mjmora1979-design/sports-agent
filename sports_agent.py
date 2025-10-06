from scraper_lines import scrape_game_lines
from scraper_props import scrape_props
from scraper_injuries import scrape_injuries
import datetime

def build_payload(sport="nfl", max_games=10):
    """Combine game lines, player props, and injuries into unified payload."""
    payload = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "sport": sport,
        "games": scrape_game_lines(max_games),
        "props": scrape_props(),
        "injuries": scrape_injuries()
    }

    print(f"[OK] Payload built: {len(payload['games'])} games, {len(payload['props'])} props, {len(payload['injuries'])} injuries")
    return payload
