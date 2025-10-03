import os, requests, pandas as pd
from datetime import datetime

API_KEY = os.getenv("ODDS_API_KEY", "")
API_URL = "https://api.the-odds-api.com/v4/sports"

SPORT_MAP = {
    "nfl": "americanfootball_nfl",
    "ncaaf": "americanfootball_ncaaf",
    "nba": "basketball_nba",
    "mlb": "baseball_mlb",
    "ncaab": "basketball_ncaab"
}

# Core markets
FEATURED_MARKETS = "h2h,spreads,totals"

# Most common props (kept small for efficiency)
COMMON_PROPS = [
    "player_pass_yds",
    "player_rush_yds",
    "player_receiving_yds",
    "player_pass_tds",
    "player_anytime_td"
]

# Default sportsbooks
DEFAULT_BOOKS = "draftkings,bet365,fanduel"


def nowstamp():
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def fetch_odds(sport_key, markets, books, span="day"):
    url = f"{API_URL}/{sport_key}/odds"
    params = {
        "apiKey": API_KEY,
        "regions": "us",
        "markets": markets,
        "oddsFormat": "american",
        "bookmakers": books
    }
    params["dateFormat"] = "iso"

    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        raise Exception(f"HTTP Error {resp.status_code}: {resp.text}")
    return resp.json()


def parse_odds(data, market_key):
    rows = []
    for game in data:
        home = game.get("home_team")
        away = game.get("away_team")
        start = game.get("commence_time")
        for bm in game.get("bookmakers", []):
            book = bm.get("title")
            for mkt in bm.get("markets", []):
                if mkt.get("key") == market_key or market_key in mkt.get("key", ""):
                    for outcome in mkt.get("outcomes", []):
                        rows.append({
                            "home_team": home,
                            "away_team": away,
                            "commence_time": start,
                            "book": book,
                            "market": mkt.get("key"),
                            "name": outcome.get("name"),
                            "price": outcome.get("price")
                        })
    return rows


def run_model(mode="live", allow_api=False, survivor=False,
              used=None, double_from=13, game_filter=None,
              max_games=None, sport="nfl", include_props=False,
              books=DEFAULT_BOOKS, debug=False):

    used = used or []
    sport_id = SPORT_MAP.get(sport.lower())
    if not sport_id:
        raise Exception(f"Unsupported sport: {sport}")

    span = "week" if sport in ["nfl", "ncaaf"] else "day"

    report = []
    skipped_props = []

    if allow_api:
        # Base markets
        for key in ["h2h", "spreads", "totals"]:
            report.extend(parse_odds(fetch_odds(sport_id, FEATURED_MARKETS, books, span=span), key))

        # Props
        if include_props:
            for market in COMMON_PROPS:
                try:
                    prop_json = fetch_odds(sport_id, market, books, span=span)
                    if prop_json:
                        report.extend(parse_odds(prop_json, market))
                except Exception as e:
                    skipped_props.append(market)

    # Survivor metadata (simple placeholder)
    survivor_meta = {"week": double_from, "used": used}

    if debug:
        return report, [], survivor_meta, skipped_props
    else:
        return report, [], survivor_meta


def save_excel(report, prev, path, survivor=None):
    df = pd.DataFrame(report)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Report", index=False)
        pd.DataFrame(prev).to_excel(writer, sheet_name="Prev", index=False)
        if survivor:
            pd.DataFrame([survivor]).to_excel(writer, sheet_name="Survivor", index=False)
