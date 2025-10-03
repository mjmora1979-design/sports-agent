import os, datetime
import pandas as pd
import nfl_data_py as nfl
from sportsbook_api import get_odds_for_sport
from sheets_writer import log_to_sheets

# -------------------------
# Week detection (NFL/NCAAF)
# -------------------------

def get_current_football_week():
    """Get NFL/NCAAF current week from nfl_data_py schedules."""
    try:
        year = datetime.date.today().year
        schedule = nfl.import_schedules([year])

        today = datetime.datetime.utcnow().date()
        upcoming = schedule[schedule['gameday'] >= str(today)]
        if not upcoming.empty:
            return int(upcoming.iloc[0]['week'])
        return int(schedule['week'].max())
    except Exception as e:
        print("Week detection failed, fallback:", e)
        return datetime.date.today().isocalendar()[1]  # ISO week fallback

# -------------------------
# Payload builder
# -------------------------

def build_payload(sport, allow_api=False, game_filter=None, max_games=None):
    """Main odds + props payload builder."""
    week = None
    if sport in ["nfl", "ncaaf"]:
        week = get_current_football_week()

    start = datetime.datetime.utcnow().isoformat()
    end = (datetime.datetime.utcnow() + datetime.timedelta(days=7)).isoformat()

    games = []
    rows_for_sheets = []

    if allow_api:
        odds = get_odds_for_sport(sport, start, end)
        for ev in odds:
            home = ev.get("home_team")
            away = ev.get("away_team")
            event_id = ev.get("id")
            commence = ev.get("commence_time")

            game = {
                "home_team": home,
                "away_team": away,
                "commence_time": commence,
                "books": ev.get("books", {}),
                "summary": {}  # TODO: add neutral best-price summary logic
            }
            games.append(game)

            # Flatten for sheets logging
            for book, data in ev.get("books", {}).items():
                for market, lines in data.get("markets", {}).items():
                    for line in lines:
                        rows_for_sheets.append({
                            "timestamp_utc": datetime.datetime.utcnow().isoformat() + "Z",
                            "event_id": event_id,
                            "commence_time": commence,
                            "home": home,
                            "away": away,
                            "book": book,
                            "market": market,
                            "label": line.get("label",""),
                            "price": line.get("price",""),
                            "point_or_line": line.get("point","")
                        })

    # ✅ Write to Sheets if enabled
    if rows_for_sheets:
        log_to_sheets(sport, rows_for_sheets)

    payload = {
        "status": "success",
        "week": week,
        "games": games,
        "survivor": {
            "used": [],
            "week": week
        }
    }
    return payload

# -------------------------
# Excel Export (optional)
# -------------------------

def to_excel(payload):
    """Return Excel bytes from payload."""
    games = payload.get("games", [])
    df = pd.DataFrame(games)
    output = pd.ExcelWriter("output.xlsx", engine="xlsxwriter")
    df.to_excel(output, index=False, sheet_name="games")
    survivor_df = pd.DataFrame([payload.get("survivor", {})])
    survivor_df.to_excel(output, index=False, sheet_name="survivor")
    output.close()
    with open("output.xlsx", "rb") as f:
        return f.read()
