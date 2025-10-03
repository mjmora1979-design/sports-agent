import os
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import json

# Get API key from environment
SPORTSBOOK_API_KEY = os.getenv("SPORTSBOOK_API_KEY")

BASE_URL = "https://sportsbook-api2.p.rapidapi.com/api/v1/odds"

HEADERS = {
    "X-RapidAPI-Key": SPORTSBOOK_API_KEY,
    "X-RapidAPI-Host": "sportsbook-api2.p.rapidapi.com"
}

# Map user input to Sportsbook API sports
SPORT_MAP = {
    "nfl": "american_football_nfl",
    "ncaaf": "american_football_ncaaf",
    "nba": "basketball_nba",
    "mlb": "baseball_mlb",
    "ncaab": "basketball_ncaab"
}

# Default bookmaker list
DEFAULT_BOOKS = ["draftkings", "fanduel", "bet365"]


def nowstamp():
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def fetch_odds(sport: str, days_ahead: int = 7, books: list = None):
    """
    Fetch odds from Sportsbook API.
    - sport: "nfl", "ncaaf", etc.
    - days_ahead: how many days forward to grab games
    - books: list of bookmaker keys (defaults to DraftKings/FanDuel/Bet365)
    """
    if sport not in SPORT_MAP:
        raise ValueError(f"Unsupported sport: {sport}")

    end_date = (datetime.now(timezone.utc) + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    params = {
        "sport": SPORT_MAP[sport],
        "region": "us",
        "mkt": "h2h,spreads,totals",
        "date": end_date
    }

    response = requests.get(BASE_URL, headers=HEADERS, params=params, timeout=20)

    if response.status_code != 200:
        raise RuntimeError(f"API Error {response.status_code}: {response.text}")

    data = response.json()
    events = data.get("events", [])

    results = []
    for event in events:
        home = event.get("homeTeam")
        away = event.get("awayTeam")
        start = event.get("commenceTime")

        for market in event.get("markets", []):
            market_type = market.get("key")
            for outcome in market.get("outcomes", []):
                book = outcome.get("bookmaker")
                if books and book.lower() not in books:
                    continue

                results.append({
                    "home_team": home,
                    "away_team": away,
                    "commence_time": start,
                    "market": market_type,
                    "book": book,
                    "name": outcome.get("name"),
                    "price": outcome.get("price")
                })

    return results


def run_model(mode="live", allow_api=True, sport="nfl", survivor=False,
              used=None, double_from=13, game_filter=None,
              max_games=None, books=None):
    """
    Run the model wrapper (currently just pulls odds).
    """
    if not allow_api:
        return [], [], {"week": double_from, "used": used or []}

    results = fetch_odds(sport=sport, days_ahead=(7 if sport in ["nfl", "ncaaf"] else 1),
                         books=books or DEFAULT_BOOKS)

    return results, [], {"week": double_from, "used": used or []}


def save_excel(report, prev, filename, survivor=None):
    """
    Save odds results to Excel for testing.
    """
    df = pd.DataFrame(report)
    df.to_excel(filename, index=False)
