import requests
from bs4 import BeautifulSoup
import datetime

def scrape_game_lines(max_games=16):
    """Scrape NFL lines (spread, total, ML) from Action Network."""
    url = "https://www.actionnetwork.com/nfl/odds"
    games = []

    try:
        html = requests.get(url, timeout=20).text
        soup = BeautifulSoup(html, "html.parser")

        matchups = soup.select("div.game")  # each game block
        for m in matchups[:max_games]:
            teams = [t.text.strip() for t in m.select("div.team-name")]
            odds = [o.text.strip() for o in m.select("div.odds-value")]

            if len(teams) == 2:
                game = {
                    "matchup": f"{teams[0]} vs {teams[1]}",
                    "spread": odds[0] if len(odds) > 0 else None,
                    "total": odds[1] if len(odds) > 1 else None,
                    "moneyline": odds[2] if len(odds) > 2 else None,
                    "source": "ActionNetwork",
                    "timestamp": datetime.datetime.utcnow().isoformat()
                }
                games.append(game)

        print(f"[OK] Scraped {len(games)} NFL games from Action Network odds.")
    except Exception as e:
        print(f"[ERROR] scrape_game_lines: {e}")

    return games
