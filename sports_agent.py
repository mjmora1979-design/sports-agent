import os
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import openpyxl

# -----------------------------
# Sports mapping (Odds API keys)
# -----------------------------
SPORTS = {
    "nfl": "americanfootball_nfl",
    "ncaaf": "americanfootball_ncaaf",
    "nba": "basketball_nba",
    "mlb": "baseball_mlb"
}

API_KEY = os.environ.get("ODDS_API_KEY")
API_URL = "https://api.the-odds-api.com/v4/sports/{sport}/odds"

# -----------------------------
# Helper: current UTC timestamp
# -----------------------------
def nowstamp():
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

# -----------------------------
# Fetch odds
# -----------------------------
def get_global_odds(allow_api: bool = False, sport: str = "nfl"):
    if not allow_api:
        return []

    if sport not in SPORTS:
        raise ValueError(f"Unsupported sport: {sport}")

    sport_key = SPORTS[sport]
    url = API_URL.format(sport=sport_key)

    params = {
        "apiKey": API_KEY,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american"
    }

    resp = requests.get(url, params=params)
    resp.raise_for_status()
    return resp.json()

# -----------------------------
# Build report
# -----------------------------
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
    if used is None:
        used = []

    games = get_global_odds(allow_api=allow_api, sport=sport)

    now = datetime.now(timezone.utc)
    report = []

    for g in games:
        try:
            commence = datetime.fromisoformat(g["commence_time"].replace("Z", "+00:00"))

            # NFL/NCAAF = full week, NBA/MLB = today only
            if sport in ["nfl", "ncaaf"]:
                if not (now <= commence <= now + timedelta(days=7)):
                    continue
            else:
                if commence.date() != now.date():
                    continue

            for book in g.get("bookmakers", []):
                for market in book.get("markets", []):
                    for outcome in market.get("outcomes", []):
                        report.append({
                            "commence_time": commence.isoformat(),
                            "home_team": g.get("home_team"),
                            "away_team": g.get("away_team"),
                            "book": book.get("title"),
                            "market": market.get("key"),
                            "name": outcome.get("name"),
                            "price": outcome.get("price")
                        })

        except Exception as e:
            print(f"Error parsing game: {e}")
            continue

    if max_games:
        report = report[:max_games]

    survivor_info = {"week": double_from, "used": used}

    return report, None, survivor_info

# -----------------------------
# Save Excel
# -----------------------------
def save_excel(report, prev, filename, survivor=None):
    df = pd.DataFrame(report)
    with pd.ExcelWriter(filename, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Report")
        if survivor:
            pd.DataFrame([survivor]).to_excel(writer, index=False, sheet_name="Survivor")
