import requests
from bs4 import BeautifulSoup
import datetime

def scrape_game_lines(max_games=10):
    """Scrape NFL game lines (spread, total, ML) from CBS Sports."""
    url = "https://www.cbssports.com/nfl/odds/"
    lines = []
    try:
        html = requests.get(url, timeout=15).text
        soup = BeautifulSoup(html, "html.parser")
        games = soup.select("div.TableBaseWrapper")

        for game in games[:max_games]:
            matchup = game.select_one("span.TeamName").text if game.select_one("span.TeamName") else None
            teams = [t.text.strip() for t in game.select("span.TeamName")]
            odds = [o.text.strip() for o in game.select("td.OddsCell")]

            if len(teams) == 2 and odds:
                entry = {
                    "game": f"{teams[0]} vs {teams[1]}",
                    "spread": odds[0] if len(odds) > 0 else None,
                    "total": odds[1] if len(odds) > 1 else None,
                    "moneyline": odds[2] if len(odds) > 2 else None,
                    "timestamp": datetime.datetime.utcnow().isoformat()
                }
                lines.append(entry)

        print(f"[OK] Scraped {len(lines)} NFL games from CBS Sports odds page")
    except Exception as e:
        print(f"[ERROR] scrape_game_lines: {e}")
    return lines
