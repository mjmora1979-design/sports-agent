"""
fetch_historical_odds.py
------------------------
Scrapes historical NFL odds and props from Covers.com for past weeks
and saves them into data/historical_odds in the same JSON format your
model expects (for backtesting calibration).
"""

import os, json, requests
from bs4 import BeautifulSoup
from datetime import datetime

def fetch_week_odds(week_number, season=2025):
    url = f"https://www.covers.com/sport/football/nfl/odds?selectedDate=2025-09-{7+week_number*7}"
    print(f"[INFO] Fetching Week {week_number} odds → {url}")
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(response.text, "html.parser")

    games = []
    for matchup in soup.select(".cmg_matchup_list_game"):
        try:
            teams = [t.text.strip() for t in matchup.select(".cmg_team_name")]
            odds = [o.text.strip().replace("+", "") for o in matchup.select(".cmg_matchup_list_odds")]
            if len(teams) == 2 and len(odds) >= 2:
                games.append({
                    "home_team": teams[1],
                    "away_team": teams[0],
                    "home_ml": int(odds[1]) if odds[1] else None,
                    "away_ml": int(odds[0]) if odds[0] else None,
                    "bookmaker": "covers"
                })
        except Exception as e:
            print(f"[WARN] Failed to parse one matchup: {e}")

    os.makedirs("data/historical_odds", exist_ok=True)
    filename = f"data/historical_odds/{season}_week{week_number}_opening.json"
    with open(filename, "w") as f:
        json.dump({"events": games}, f, indent=2)
    print(f"✅ Saved {len(games)} games → {filename}")
    return filename

if __name__ == "__main__":
    for wk in range(1, 6):
        fetch_week_odds(wk)
