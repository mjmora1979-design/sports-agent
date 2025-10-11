"""
scraper_results.py
------------------
Pulls historical NFL results from Pro-Football-Reference.
Provides a callable function fetch_game_results() for use in backtesting.
"""

import requests
import pandas as pd
from bs4 import BeautifulSoup

def fetch_game_results(year: int = 2025, save_path: str = "final_scores.csv") -> pd.DataFrame:
    """Scrape NFL results for a given year and save to CSV."""
    url = f"https://www.pro-football-reference.com/years/{year}/games.htm"
    print(f"[INFO] Fetching NFL game results from: {url}")
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    if res.status_code != 200:
        raise Exception(f"Failed to fetch page: HTTP {res.status_code}")

    soup = BeautifulSoup(res.text, "html.parser")
    table = soup.find("table", {"id": "games"})
    if not table:
        raise Exception("Could not locate games table on page.")

    df = pd.read_html(str(table))[0]
    df = df.dropna(subset=["Winner/tie", "Loser/tie"])
    df = df.rename(columns={
        "Winner/tie": "winner",
        "Loser/tie": "loser",
        "Home/Neutral": "location",
        "Week": "week"
    })

    df["home_team"] = df.apply(
        lambda r: r["winner"] if r["location"] != "@" else r["loser"], axis=1
    )
    df["away_team"] = df.apply(
        lambda r: r["loser"] if r["location"] != "@" else r["winner"], axis=1
    )

    df = df[["week", "home_team", "away_team", "winner"]]
    df.to_csv(save_path, index=False)
    print(f"✅ Saved {len(df)} results to {save_path}")
    return df


if __name__ == "__main__":
    fetch_game_results(2025)
