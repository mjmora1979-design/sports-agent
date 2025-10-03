import os
import requests
import pandas as pd
from datetime import datetime
from openpyxl import Workbook

# =========================
# Sport Key Mapping
# =========================
SPORT_KEY_MAP = {
    "nfl": "americanfootball_nfl",
    "football": "americanfootball_nfl",
    "nba": "basketball_nba",
    "basketball": "basketball_nba",
    "mlb": "baseball_mlb",
    "baseball": "baseball_mlb",
    "nhl": "icehockey_nhl",
    "hockey": "icehockey_nhl",
}

def get_sport_key(user_input: str) -> str:
    """Translate user-friendly sport names into API keys."""
    if not user_input:
        return "americanfootball_nfl"  # Default NFL
    key = user_input.lower().strip()
    if key in SPORT_KEY_MAP:
        return SPORT_KEY_MAP[key]
    raise ValueError(f"Unsupported sport '{user_input}'. Supported: {list(SPORT_KEY_MAP.keys())}")


# =========================
# API Call
# =========================
def get_global_odds(allow_api: bool = False, sport: str = "nfl"):
    """Fetch odds from The Odds API or fallback mock if allow_api is False."""
    sport_key = get_sport_key(sport)

    if not allow_api:
        # Return mock data if API not allowed
        return pd.DataFrame([
            {"home_team": "Mock Home", "away_team": "Mock Away",
             "commence_time": "2025-01-01T00:00:00Z", "book": "mock",
             "market": "h2h", "name": "Mock Team", "price": -110}
        ])

    api_key = os.getenv("ODDS_API_KEY")
    if not api_key:
        raise RuntimeError("Missing ODDS_API_KEY environment variable.")

    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
    params = {
        "apiKey": api_key,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american"
    }

    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP Error {resp.status_code}: {resp.text}")

    games = resp.json()
    rows = []
    for g in games:
        for book in g.get("bookmakers", []):
            for market in book.get("markets", []):
                for outcome in market.get("outcomes", []):
                    rows.append({
                        "home_team": g.get("home_team"),
                        "away_team": g.get("away_team"),
                        "commence_time": g.get("commence_time"),
                        "market": market.get("key"),
                        "book": book.get("title"),
                        "name": outcome.get("name"),
                        "price": outcome.get("price")
                    })
    return pd.DataFrame(rows)


# =========================
# Core Runner
# =========================
def run_model(mode="live", allow_api=False, survivor=False, used=None,
              double_from=13, game_filter=None, max_games=None, sport="nfl"):

    try:
        df = get_global_odds(allow_api=allow_api, sport=sport)
    except ValueError:
        # fallback if sport is not supported
        df = get_global_odds(allow_api=allow_api, sport="nfl")

    # Optionally filter by team name
    if game_filter:
        df = df[df["home_team"].str.contains(game_filter, case=False) |
                df["away_team"].str.contains(game_filter, case=False)]

    if max_games:
        df = df.head(max_games)

    # Survivor placeholder
    survivor_output = {"week": double_from, "used": used or []}

    return df.to_dict(orient="records"), [], survivor_output


# =========================
# Excel Export
# =========================
def save_excel(report, prev, filepath, survivor=None):
    df = pd.DataFrame(report)
    with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Report", index=False)
        if survivor:
            pd.DataFrame([survivor]).to_excel(writer, sheet_name="Survivor", index=False)


# =========================
# Timestamp Helper
# =========================
def nowstamp():
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")
