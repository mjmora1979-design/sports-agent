import os
import datetime
import pandas as pd
import io

from sportsbook_api import get_odds_for_sport
from sheets_writer import log_to_sheets

import nfl_data_py as nfl


# -------------------------
# Helpers
# -------------------------

def get_current_football_week():
    """Return the current NFL/NCAAF week using nfl_data_py, fallback to ISO calendar week."""
    try:
        season = nfl.current_season()
        schedule = nfl.import_schedules([season])
        today = datetime.datetime.utcnow().date()
        upcoming = schedule[schedule['gameday'] >= str(today)]
        if not upcoming.empty:
            return int(upcoming.iloc[0]['week'])
        return int(schedule['week'].max())
    except Exception as e:
        print("Week detection failed, fallback:", e)
        return datetime.date.today().isocalendar()[1]  # fallback


def determine_scope(sport: str):
    """Decide whether to pull weekly or daily data based on sport."""
    sport = sport.lower()
    if sport in ["nfl", "ncaaf"]:
        # Weekly window (today -> 8 days ahead)
        week = get_current_football_week()
        start = datetime.datetime.utcnow()
        end = start + datetime.timedelta(days=8)
        return {"scope": "week", "week": week, "start": start, "end": end}
    else:
        # Daily window (today only)
        today = datetime.datetime.utcnow().date()
        start = datetime.datetime.combine(today, datetime.time.min)
        end = datetime.datetime.combine(today, datetime.time.max)
        return {"scope": "day", "week": None, "start": start, "end": end}


def summarize_game(game):
    """Build neutral best-price summary for a single game."""
    summary = {
        "best_moneyline_by_team": {},
        "best_spread_by_team": {},
        "best_total": {}
    }

    # moneyline
    moneylines = {}
    for book, markets in game["books"].items():
        if "h2h" in markets:
            for team, price in markets["h2h"].items():
                if team not in moneylines or price > moneylines[team]["price"]:
                    moneylines[team] = {"book": book, "price": price}
    summary["best_moneyline_by_team"] = moneylines

    # spreads
    spreads = {}
    for book, markets in game["books"].items():
        if "spreads" in markets:
            for s in markets["spreads"]:
                team = s["name"]
                if team not in spreads or s["price"] > spreads[team]["price"]:
                    spreads[team] = {"book": book, "price": s["price"], "point": s["point"]}
    summary["best_spread_by_team"] = spreads

    # totals
    totals = {}
    for book, markets in game["books"].items():
        if "totals" in markets:
            for ou, val in markets["totals"].items():
                if ou not in totals or val["price"] > totals[ou]["price"]:
                    totals[ou] = {"book": book, "price": val["price"], "point": val["point"]}
    summary["best_total"] = totals

    return summary


# -------------------------
# Main payload builder
# -------------------------

def build_payload(sport: str, allow_api: bool = False, game_filter=None, max_games=None):
    sport = sport.lower()
    scope_info = determine_scope(sport)
    week = scope_info["week"]

    games = []

    if allow_api:
        events = get_odds_for_sport(
            sport,
            scope_info["start"],
            scope_info["end"],
            books=os.getenv("BOOKS_DEFAULT", "draftkings,fanduel").split(",")
        )

        for event in events:
            game = {
                "home_team": event.get("home_team"),
                "away_team": event.get("away_team"),
                "commence_time": event.get("commence_time"),
                "books": event.get("books", {})
            }
            game["summary"] = summarize_game(game)
            games.append(game)

        # Optional filter
        if game_filter:
            games = [g for g in games if game_filter.lower() in g["home_team"].lower()
                     or game_filter.lower() in g["away_team"].lower()]
        if max_games:
            games = games[:max_games]

        # Sheets logging (optional)
        if os.getenv("SHEETS_ENABLED", "0") == "1":
            try:
                log_to_sheets(sport, games)
            except Exception as e:
                print("Sheets logging failed:", e)

    payload = {
        "status": "success",
        "week": week if week else 0,
        "games": games,
        "survivor": {"used": [], "week": week if week else 0}
    }
    return payload


# -------------------------
# Excel Export
# -------------------------

def to_excel(payload: dict) -> bytes:
    """Flatten JSON payload into Excel with two sheets."""
    games = payload.get("games", [])
    survivor = payload.get("survivor", {})

    # Flatten games
    flat_games = []
    for g in games:
        row = {
            "home_team": g["home_team"],
            "away_team": g["away_team"],
            "commence_time": g["commence_time"]
        }
        for book, markets in g["books"].items():
            row[f"{book}_moneyline"] = markets.get("h2h", {})
            row[f"{book}_spreads"] = markets.get("spreads", [])
            row[f"{book}_totals"] = markets.get("totals", {})
        flat_games.append(row)

    df_games = pd.DataFrame(flat_games)
    df_survivor = pd.DataFrame([survivor])

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df_games.to_excel(writer, sheet_name="games", index=False)
        df_survivor.to_excel(writer, sheet_name="survivor", index=False)
    return output.getvalue()
