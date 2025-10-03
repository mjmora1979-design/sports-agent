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
# Helpers
# -------------------------

def summarize_best_prices(game):
    """Return neutral summary with best ML/spread/total across books."""
    summary = {
        "best_moneyline_by_team": {},
        "best_spread_by_team": {},
        "best_total": {}
    }

    books = game.get("books", {})
    # --- Moneyline
    for book, data in books.items():
        for team, price in data.get("h2h", {}).items():
            if team not in summary["best_moneyline_by_team"] or price > summary["best_moneyline_by_team"][team]["price"]:
                summary["best_moneyline_by_team"][team] = {"book": book, "price": price}

    # --- Spreads
    for book, data in books.items():
        for spread in data.get("spreads", []):
            team = spread.get("name")
            price = spread.get("price")
            point = spread.get("point")
            if team not in summary["best_spread_by_team"] or price > summary["best_spread_by_team"][team]["price"]:
                summary["best_spread_by_team"][team] = {"book": book, "price": price, "point": point}

    # --- Totals
    for book, data in books.items():
        totals = data.get("totals", {})
        for side in ["Over", "Under"]:
            if side in totals:
                price = totals[side].get("price")
                point = totals[side].get("point")
                if side not in summary["best_total"] or price > summary["best_total"][side]["price"]:
                    summary["best_total"][side] = {"book": book, "price": price, "point": point}

    return summary

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

            # Normalize book structure (DraftKings/FanDuel only)
            books = {}
            for book, data in ev.get("books", {}).items():
                book_name = "DraftKings" if "draftkings" in book.lower() else \
                            "FanDuel" if "fanduel" in book.lower() else book
                books[book_name] = {
                    "h2h": data.get("h2h", {}),
                    "spreads": data.get("spreads", []),
                    "totals": data.get("totals", {}),
                    "props": data.get("props", {})
                }

            game = {
                "home_team": home,
                "away_team": away,
                "commence_time": commence,
                "books": books,
                "summary": summarize_best_prices({"books": books})
            }
            games.append(game)

            # Flatten for sheets logging
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
                for spread in data.get("spreads", []):
                    rows_for_sheets.append({
                        "timestamp_utc": datetime.datetime.utcnow().isoformat() + "Z",
                        "event_id": event_id,
                        "commence_time": commence,
                        "home": home,
                        "away": away,
                        "book": book,
                        "market": "spread",
                        "label": spread.get("name"),
                        "price": spread.get("price"),
                        "point_or_line": spread.get("point")
                    })
                for side, val in data.get("totals", {}).items():
                    rows_for_sheets.append({
                        "timestamp_utc": datetime.datetime.utcnow().isoformat() + "Z",
                        "event_id": event_id,
                        "commence_time": commence,
                        "home": home,
                        "away": away,
                        "book": book,
                        "market": "total",
                        "label": side,
                        "price": val.get("price"),
                        "point_or_line": val.get("point")
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
