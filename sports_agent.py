import os
import requests
import pandas as pd
import numpy as np
import datetime
from openpyxl import Workbook

API_KEY = os.getenv("ODDS_API_KEY")

# Map user-friendly sport codes to Odds API sport keys
SPORT_KEYS = {
    "nfl": "americanfootball_nfl",
    "ncaaf": "americanfootball_ncaaf",
    "nba": "basketball_nba",
    "mlb": "baseball_mlb",
    "ncaab": "basketball_ncaab"
}

def nowstamp():
    return datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")

def get_global_odds(allow_api: bool = False, sport: str = "nfl"):
    """
    Fetch odds from the Odds API for the given sport.
    NFL & NCAAF -> fetch the entire week of games
    Others -> fetch day of game
    """
    if not allow_api:
        raise ValueError("API access disabled. Set allow_api true or header X-ALLOW-API=1")

    sport_id = SPORT_KEYS.get(sport.lower())
    if not sport_id:
        raise ValueError(f"Unsupported sport: {sport}")

    # Determine scheduling
    today = datetime.datetime.utcnow()
    if sport.lower() in ["nfl", "ncaaf"]:
        # Full week window (Mon–Sun)
        start_date = today - datetime.timedelta(days=today.weekday())  # Monday
        end_date = start_date + datetime.timedelta(days=7)
    else:
        # Just today's games
        start_date = today
        end_date = today + datetime.timedelta(days=1)

    url = (
        f"https://api.the-odds-api.com/v4/sports/{sport_id}/odds/"
        f"?regions=us&markets=h2h,spreads,totals"
        f"&dateFormat=iso&apiKey={API_KEY}"
    )

    resp = requests.get(url)
    if resp.status_code != 200:
        raise ValueError(f"HTTP Error {resp.status_code}: {resp.reason}")

    games = resp.json()

    # Filter games within time window
    results = []
    for g in games:
        try:
            commence = datetime.datetime.fromisoformat(g["commence_time"].replace("Z", "+00:00"))
            if not (start_date <= commence < end_date):
                continue

            for book in g.get("bookmakers", []):
                for market in book.get("markets", []):
                    for outcome in market.get("outcomes", []):
                        results.append({
                            "home_team": g.get("home_team"),
                            "away_team": g.get("away_team"),
                            "commence_time": g.get("commence_time"),
                            "book": book.get("title"),
                            "market": market.get("key"),
                            "name": outcome.get("name"),
                            "price": outcome.get("price")
                        })
        except Exception as e:
            print("Error parsing game:", e)
            continue

    return pd.DataFrame(results)


def run_model(
    mode="live",
    allow_api=False,
    survivor=False,
    used=None,
    double_from=13,
    game_filter=None,
    max_games=None,
    sport="nfl"
):
    """
    Run the odds model wrapper.
    """
    if used is None:
        used = []

    # Pull odds data
    df = get_global_odds(allow_api=allow_api, sport=sport)

    # Optional filtering
    if game_filter:
        df = df[df["home_team"].str.contains(game_filter, case=False) |
                df["away_team"].str.contains(game_filter, case=False)]

    if max_games:
        df = df.head(int(max_games))

    # Survivor stub
    survivor_state = {"week": double_from, "used": used}

    return df.to_dict(orient="records"), None, survivor_state


def save_excel(report, prev, filepath, survivor=None):
    """
    Save report to Excel file.
    """
    df = pd.DataFrame(report)
    with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Report")
        if survivor:
            pd.DataFrame([survivor]).to_excel(writer, index=False, sheet_name="Survivor")
