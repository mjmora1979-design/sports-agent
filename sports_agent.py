import os, datetime
import pandas as pd
import nfl_data_py as nfl
from sportsbook_api import get_events, get_odds
from sheets_writer import log_to_sheets

def get_current_football_week():
    """Get NFL/NCAAF current week from nfl_data_py schedules, fallback to ISO week."""
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

def build_payload(sport, allow_api=True, max_games=None):
    """Main payload builder (events + odds)."""
    week = get_current_football_week() if sport in ["nfl", "ncaaf"] else None

    start = datetime.datetime.utcnow().isoformat()
    end = (datetime.datetime.utcnow() + datetime.timedelta(days=7)).isoformat()

    games = []
    rows_for_sheets = []

    if allow_api:
        try:
            events = get_events(sport, start, end)
            event_ids = [ev["id"] for ev in events]
            if max_games:
                event_ids = event_ids[:max_games]

            odds = get_odds(sport, event_ids, markets=["h2h","spreads","totals","player_props"])

            for ev in events:
                eid = ev["id"]
                game_odds = next((o for o in odds if o.get("id") == eid), {})
                game = {
                    "home_team": ev.get("home_team"),
                    "away_team": ev.get("away_team"),
                    "commence_time": ev.get("commence_time"),
                    "books": game_odds.get("books", {})
                }
                games.append(game)

                # Flatten for sheets logging
                for book, data in game["books"].items():
                    for team, price in data.get("h2h", {}).items():
                        rows_for_sheets.append({
                            "timestamp_utc": datetime.datetime.utcnow().isoformat() + "Z",
                            "event_id": eid,
                            "commence_time": ev.get("commence_time"),
                            "home": ev.get("home_team"),
                            "away": ev.get("away_team"),
                            "book": book,
                            "market": "moneyline",
                            "label": team,
                            "price": price,
                            "point_or_line": ""
                        })

        except Exception as e:
            print("[ERROR] build_payload failed:", e)

    # ✅ Log to Sheets if enabled
    if rows_for_sheets:
        log_to_sheets(sport, rows_for_sheets)

    return {
        "status": "success",
        "week": week,
        "games": games,
        "survivor": {"used": [], "week": week}
    }

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
