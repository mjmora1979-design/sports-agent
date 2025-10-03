import requests
import pandas as pd
import datetime as dt
import os

# Default sportsbooks (swapped BetMGM -> Bet365)
DEFAULT_BOOKS = ["draftkings", "fanduel", "bet365"]

# Mapping of supported sports
SPORT_IDS = {
    "nfl": "americanfootball_nfl",
    "ncaaf": "americanfootball_ncaaf",
    "nba": "basketball_nba",
    "ncaab": "basketball_ncaab",
    "mlb": "baseball_mlb"
}

API_KEY = os.getenv("ODDS_API_KEY", "DEMO_KEY")
BASE_URL = "https://api.the-odds-api.com/v4/sports"

def nowstamp():
    return dt.datetime.utcnow().strftime("%Y%m%d_%H%M%S")

def get_global_odds(sport: str = "nfl", allow_api: bool = False, books=None, full_week=False):
    """
    Pulls odds for given sport.
    - sport: nfl, ncaaf, nba, ncaab, mlb
    - allow_api: True to call API
    - books: list of sportsbooks (defaults to DEFAULT_BOOKS)
    - full_week: for nfl/ncaaf, get all games in next 7 days
    """
    if books is None:
        books = DEFAULT_BOOKS

    if sport not in SPORT_IDS:
        raise ValueError(f"Unsupported sport: {sport}")

    sport_key = SPORT_IDS[sport]

    if not allow_api:
        return []

    params = {
        "apiKey": API_KEY,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american",
        "bookmakers": ",".join(books)
    }

    url = f"{BASE_URL}/{sport_key}/odds"

    # if NFL or NCAAF and full_week flag is set → get all games for 7 days
    if full_week and sport in ["nfl", "ncaaf"]:
        params["daysFrom"] = 7

    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        raise Exception(f"API error {resp.status_code}: {resp.text}")

    games = resp.json()
    rows = []

    for g in games:
        home = g.get("home_team")
        away = g.get("away_team")
        time = g.get("commence_time")

        for book in g.get("bookmakers", []):
            book_key = book.get("key")
            if book_key not in books:
                continue
            for market in book.get("markets", []):
                mkt = market.get("key")
                for outcome in market.get("outcomes", []):
                    rows.append({
                        "home_team": home,
                        "away_team": away,
                        "commence_time": time,
                        "book": book_key.title(),
                        "market": mkt,
                        "name": outcome.get("name"),
                        "price": outcome.get("price")
                    })

    return rows


def run_model(mode="live", allow_api=False, survivor=False, used=None,
              double_from=13, game_filter=None, max_games=None,
              sport="nfl", books=None):
    """
    Run odds fetch and light survivor logic.
    """
    if used is None:
        used = []

    if books is None:
        books = DEFAULT_BOOKS

    full_week = (sport in ["nfl", "ncaaf"])

    rows = get_global_odds(
        sport=sport,
        allow_api=allow_api,
        books=books,
        full_week=full_week
    )

    df = pd.DataFrame(rows)

    # Filter explicitly to requested books again (safety)
    if not df.empty:
        df = df[df["book"].str.lower().isin([b.lower() for b in books])]

        # Sort by kickoff time
        df["commence_time"] = pd.to_datetime(df["commence_time"], errors="coerce")
        df = df.sort_values("commence_time")

    if max_games and not df.empty:
        df = df.head(max_games)

    survivor_state = {"used": used, "week": double_from}

    return df.to_dict(orient="records"), None, survivor_state


def save_excel(report, prev, path, survivor=None):
    df = pd.DataFrame(report)

    # Ensure sorted order in Excel
    if not df.empty and "commence_time" in df.columns:
        df["commence_time"] = pd.to_datetime(df["commence_time"], errors="coerce")
        df = df.sort_values("commence_time")

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        if not df.empty:
            df.to_excel(writer, sheet_name="Report", index=False)
        if survivor:
            pd.DataFrame([survivor]).to_excel(writer, sheet_name="Survivor", index=False)
