import os, datetime
import pandas as pd
import nfl_data_py as nfl
from sportsbook_api import get_odds
from sheets_writer import log_to_sheets

def get_current_football_week():
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
        return datetime.date.today().isocalendar()[1]

def build_payload(sport, allow_api=False, game_filter=None, max_games=None):
    week = None
    if sport in ["nfl", "ncaaf"]:
        week = get_current_football_week()

    start = datetime.datetime.utcnow().isoformat()
    end = (datetime.datetime.utcnow() + datetime.timedelta(days=7)).isoformat()

    games, rows_for_sheets = [], []

    if allow_api:
        odds = get_odds(sport)
        if max_games:
            odds = odds[:max_games]

        for ev in odds:
            home, away, event_id, commence = ev.get("home_team"), ev.get("away_team"), ev.get("id"), ev.get("commence_time")
            books = ev.get("books", {})

            game = {
                "home_team": home,
                "away_team": away,
                "commence_time": commence,
                "books": books
            }
            games.append(game)

            for book, data in books.items():
                for team, price in data.get("h2h", {}).items():
                    rows_for_sheets.append({
                        "timestamp_utc": datetime.datetime.utcnow().isoformat() + "Z",
                        "event_id": event_id,
                        "commence_time": commence,
                        "home": home,
                        "away": away,
                        "book": book,
                        "market": "moneyline",
                        "label": team,
                        "price": price,
                        "point_or_line": ""
                    })

    if rows_for_sheets:
        log_to_sheets(sport, rows_for_sheets)

    return {
        "status": "success",
        "week": week,
        "games": games,
        "survivor": {"used": [], "week": week} if sport == "nfl" else {}
    }

def to_excel(payload):
    games = payload.get("games", [])
    df = pd.DataFrame(games)
    output = pd.ExcelWriter("output.xlsx", engine="xlsxwriter")
    df.to_excel(output, index=False, sheet_name="games")
    if payload.get("survivor"):
        pd.DataFrame([payload["survivor"]]).to_excel(output, index=False, sheet_name="survivor")
    output.close()
    with open("output.xlsx", "rb") as f:
        return f.read()
