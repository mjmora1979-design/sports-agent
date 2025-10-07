import requests
from bs4 import BeautifulSoup
import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

def scrape_game_lines(max_games=16):
    url = "https://www.actionnetwork.com/nfl/odds"
    games = []

    try:
        html = requests.get(url, headers=HEADERS, timeout=25).text
        soup = BeautifulSoup(html, "html.parser")

        # Try generic selectors (Action Network sometimes changes class names)
        for game in soup.select("div.odds-table-container")[:max_games]:
            matchup = game.find("div", class_="game-title")
            lines = game.find_all("div", class_="sportsbook-odds")

            spread = lines[0].get_text(strip=True) if len(lines) > 0 else None
            total = lines[1].get_text(strip=True) if len(lines) > 1 else None
            moneyline = lines[2].get_text(strip=True) if len(lines) > 2 else None

            if matchup:
                games.append({
                    "matchup": matchup.text.strip(),
                    "spread": spread,
                    "total": total,
                    "moneyline": moneyline,
                    "source": "ActionNetwork",
                    "timestamp": datetime.datetime.utcnow().isoformat()
                })

        print(f"[OK] Scraped {len(games)} games from Action Network.")
    except Exception as e:
        print(f"[ERROR] scrape_game_lines: {e}")

    return games
