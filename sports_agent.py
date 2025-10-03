import os
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone

# Default sportsbooks
DEFAULT_BOOKS = ["draftkings", "fanduel", "bet365"]

# Mapping of sport code to Odds API sport key
SPORT_IDS = {
    "nfl": "americanfootball_nfl",
    "ncaaf": "americanfootball_ncaaf",
    "nba": "basketball_nba",
    "ncaab": "basketball_ncaab",
    "mlb": "baseball_mlb"
}

API_KEY = os.getenv("ODDS_API_KEY")
BASE_ODDS_URL = "https://api.the-odds-api.com/v4/sports/{sport}/odds"
BASE_EVENT_URL = "https://api.the-odds-api.com/v4/sports/{sport}/events/{event_id}/odds"

# The prop markets we support (small common set)
PROP_MARKETS_BY_SPORT = {
    "nfl": ["player_pass_yds", "player_rush_yds", "player_receptions", "player_pass_tds"],
    "ncaaf": ["player_pass_yds", "player_rush_yds", "player_receptions", "player_pass_tds"],
    "nba": ["player_points", "player_rebounds", "player_assists"],
    "ncaab": ["player_points", "player_rebounds", "player_assists"],
    "mlb": ["batter_home_runs", "batter_hits", "batter_rbis"]
}

def nowstamp():
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

def get_bulk_odds(sport, books, full_week=False):
    """
    Fetch bulk odds (h2h, spreads, totals) from /odds endpoint.
    """
    sport_id = SPORT_IDS.get(sport)
    if sport_id is None:
        raise ValueError(f"Unsupported sport: {sport}")

    params = {
        "apiKey": API_KEY,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "bookmakers": ",".join(books)
    }
    if full_week and sport in ["nfl", "ncaaf"]:
        params["daysFrom"] = 7

    url = BASE_ODDS_URL.format(sport=sport_id)
    resp = requests.get(url, params=params, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"Bulk odds API error {resp.status_code}: {resp.text}")
    return resp.json()

def get_event_props(sport, event_id, books, prop_markets):
    """
    Fetch only props for one game via event-level endpoint.
    """
    sport_id = SPORT_IDS.get(sport)
    if sport_id is None:
        return []

    markets_str = ",".join(prop_markets)
    params = {
        "apiKey": API_KEY,
        "regions": "us",
        "markets": markets_str,
        "bookmakers": ",".join(books)
    }
    url = BASE_EVENT_URL.format(sport=sport_id, event_id=event_id)

    resp = requests.get(url, params=params, timeout=30)
    if resp.status_code != 200:
        # Not all events support props; just skip
        return []
    return resp.json()

def run_model(
    mode="live",
    allow_api=False,
    survivor=False,
    used=None,
    double_from=13,
    game_filter=None,
    max_games=None,
    sport="nfl",
    books=None,
    include_props=False
):
    if used is None:
        used = []
    if books is None:
        books = DEFAULT_BOOKS

    full_week = (sport in ["nfl", "ncaaf"])

    bulk = get_bulk_odds(sport, books, full_week=full_week)

    results = []

    for game in bulk:
        event_id = game.get("id")
        home = game.get("home_team")
        away = game.get("away_team")
        commence = game.get("commence_time")

        # Process markets in bulk
        for book in game.get("bookmakers", []):
            book_key = book.get("key")
            if book_key not in books:
                continue
            for market in book.get("markets", []):
                for out in market.get("outcomes", []):
                    results.append({
                        "event_id": event_id,
                        "commence_time": commence,
                        "home_team": home,
                        "away_team": away,
                        "book": book_key.title(),
                        "market": market.get("key"),
                        "name": out.get("name"),
                        "price": out.get("price")
                    })

        # If props requested, fetch them and merge
        if include_props:
            prop_markets = PROP_MARKETS_BY_SPORT.get(sport, [])
            ev = get_event_props(sport, event_id, books, prop_markets)
            for book in ev.get("bookmakers", []):
                bk = book.get("key")
                if bk not in books:
                    continue
                for market in book.get("markets", []):
                    mkey = market.get("key")
                    for out in market.get("outcomes", []):
                        results.append({
                            "event_id": event_id,
                            "commence_time": commence,
                            "home_team": home,
                            "away_team": away,
                            "book": bk.title(),
                            "market": mkey,
                            "name": out.get("name"),
                            "price": out.get("price")
                        })

    # Convert to DataFrame to sort/group
    df = pd.DataFrame(results)
    if not df.empty:
        df["commence_time"] = pd.to_datetime(df["commence_time"], utc=True, errors="coerce")
        df = df.sort_values(["commence_time", "home_team", "away_team", "market", "book"])

    if max_games and not df.empty:
        df = df.head(max_games)

    survivor_state = {"used": used, "week": double_from}

    return df.to_dict(orient="records"), None, survivor_state

def save_excel(report, prev, path, survivor=None):
    df = pd.DataFrame(report)
    if not df.empty:
        df["commence_time"] = pd.to_datetime(df["commence_time"], utc=True, errors="coerce")
        df = df.sort_values(["commence_time", "home_team", "away_team", "market", "book"])

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        if not df.empty:
            df.to_excel(writer, sheet_name="Report", index=False)
        if survivor:
            pd.DataFrame([survivor]).to_excel(writer, sheet_name="Survivor", index=False)
