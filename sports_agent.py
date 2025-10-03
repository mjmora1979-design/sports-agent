import os
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone

# Default sportsbooks (can be overridden in request JSON "books")
DEFAULT_BOOKS = [
    b.strip().lower() for b in os.environ.get("DEFAULT_BOOKS", "draftkings,bet365,fanduel").split(",")
    if b.strip()
]

# Supported sports and fetch window
SPORT_META = {
    "nfl":   {"sport_id": "americanfootball_nfl",   "span": "week"},
    "ncaaf": {"sport_id": "americanfootball_ncaaf", "span": "week"},
    "nba":   {"sport_id": "basketball_nba",         "span": "day"},
    "mlb":   {"sport_id": "baseball_mlb",           "span": "day"},
    "ncaab": {"sport_id": "basketball_ncaab",       "span": "day"},
}

# Market groups
FEATURED_MARKETS = "h2h,spreads,totals"
PROP_MARKETS = "player_pass_yds,player_rush_yds,player_receiving_yds,player_pass_tds,player_anytime_td"

ODDS_API_KEY = os.environ.get("ODDS_API_KEY")

# -------------------------------------------------------------------
def nowstamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def get_sport_window(span="day"):
    """Return start and end times for the request window (day vs week)."""
    now = datetime.now(timezone.utc)
    if span == "week":
        start = now - timedelta(days=1)
        end = now + timedelta(days=7)
    else:
        start = now - timedelta(days=1)
        end = now + timedelta(days=1)
    return start, end

def fetch_odds(sport_id, markets, books, span="day"):
    """Fetch odds from The Odds API for a given sport, markets, and books."""
    if not ODDS_API_KEY:
        raise ValueError("Missing ODDS_API_KEY environment variable.")

    start, end = get_sport_window(span)
    url = f"https://api.the-odds-api.com/v4/sports/{sport_id}/odds"

    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": markets,
        "oddsFormat": "american",
        "dateFormat": "iso",
        "bookmakers": ",".join(books)
    }

    resp = requests.get(url, params=params, timeout=20)
    if resp.status_code != 200:
        raise ValueError(f"HTTP Error {resp.status_code}: {resp.text}")

    games = resp.json()
    results = []

    for g in games:
        try:
            commence = g.get("commence_time")
            commence_dt = datetime.fromisoformat(commence.replace("Z", "+00:00"))
            if not (start <= commence_dt <= end):
                continue

            for bm in g.get("bookmakers", []):
                for market in bm.get("markets", []):
                    for outcome in market.get("outcomes", []):
                        results.append({
                            "home_team": g.get("home_team"),
                            "away_team": g.get("away_team"),
                            "commence_time": commence_dt.strftime("%a, %d %b %Y %H:%M:%S GMT"),
                            "book": bm.get("title"),
                            "market": market.get("key"),
                            "name": outcome.get("name"),
                            "price": outcome.get("price"),
                        })
        except Exception as e:
            print(f"Error parsing game: {e}")

    return results

# -------------------------------------------------------------------
def run_model(
    sport="nfl",
    allow_api=False,
    include_props=False,
    books=None,
    survivor=False,
    used=None,
    double_from=13,
    game_filter=None,
    max_games=None
):
    """Main model runner: fetch odds and build a report."""
    if used is None:
        used = []

    if sport not in SPORT_META:
        raise ValueError(f"Unsupported sport: {sport}")

    sport_id = SPORT_META[sport]["sport_id"]
    span = SPORT_META[sport]["span"]

    books = [b.lower() for b in (books or DEFAULT_BOOKS)]

    # Fetch core markets
    report = []
    if allow_api:
        report.extend(fetch_odds(sport_id, FEATURED_MARKETS, books, span=span))
        if include_props:
            report.extend(fetch_odds(sport_id, PROP_MARKETS, books, span=span))

    # Survivor placeholder logic
    surv = {"week": double_from, "used": used}

    # Previous picks placeholder
    prev = []

    return report, prev, surv

# -------------------------------------------------------------------
def save_excel(report, prev, filename, survivor=None):
    """Save the report into an Excel workbook."""
    with pd.ExcelWriter(filename, engine="openpyxl") as writer:
        if report:
            pd.DataFrame(report).to_excel(writer, sheet_name="Report", index=False)
        if prev:
            pd.DataFrame(prev).to_excel(writer, sheet_name="Previous", index=False)
        if survivor:
            pd.DataFrame([survivor]).to_excel(writer, sheet_name="Survivor", index=False)
