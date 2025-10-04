import os, datetime
import pandas as pd
import nfl_data_py as nfl
from sportsbook_api import get_odds
from sheets_writer import log_to_sheets, read_from_sheets

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
    """Return neutral summary with best ML/spread/total/props across books."""
    summary = {
        "best_moneyline_by_team": {},
        "best_spread_by_team": {},
        "best_total": {},
        "best_props": {}
    }

    books = game.get("books", {})

    # Moneyline
    for book, data in books.items():
        for team, price in data.get("h2h", {}).items():
            if team not in summary["best_moneyline_by_team"] or price > summary["best_moneyline_by_team"][team]["price"]:
                summary["best_moneyline_by_team"][team] = {"book": book, "price": price}

    # Spreads
    for book, data in books.items():
        for spread in data.get("spreads", []):
            team = spread.get("name")
            price = spread.get("price")
            point = spread.get("point")
            if team not in summary["best_spread_by_team"] or price > summary["best_spread_by_team"][team]["price"]:
                summary["best_spread_by_team"][team] = {"book": book, "price": price, "point": point}

    # Totals
    for book, data in books.items():
        totals = data.get("totals", {})
        for side in ["Over", "Under"]:
            if side in totals:
                price = totals[side].get("price")
                point = totals[side].get("point")
                if side not in summary["best_total"] or price > summary["best_total"][side]["price"]:
                    summary["best_total"][side] = {"book": book, "price": price, "point": point}

    # Props
    prop_targets = ["passing_yards", "rushing_yards", "receiving_yards", "anytime_td", "passing_tds"]
    for book, data in books.items():
        props = data.get("props", {})
        for prop_name, players in props.items():
            if prop_name in prop_targets:
                if prop_name not in summary["best_props"]:
                    summary["best_props"][prop_name] = {}
                for player, lines in players.items():
                    for side, line in lines.items():
                        current = summary["best_props"][prop_name].get(player, {}).get(side)
                        if not current or line.get("price", -9999) > current["price"]:
                            if player not in summary["best_props"][prop_name]:
                                summary["best_props"][prop_name][player] = {}
                            summary["best_props"][prop_name][player][side] = {
                                "book": book,
                                "point": line.get("point"),
                                "price": line.get("price")
                            }

    return summary

# -------------------------
# Payload builder with fallback
# -------------------------

def build_payload(sport, allow_api=False, game_filter=None, max_games=None, mode=None):
    """
    Main odds + props payload builder.
    mode options:
      - "live": pulls current odds from API
      - "historical": pulls stored odds from Google Sheets
      - None/default: auto (try live, fallback to historical)
    """
    week = None
    if sport in ["nfl", "ncaaf"]:
        week = get_current_football_week()

    start = datetime.datetime.utcnow().isoformat()
    end = (datetime.datetime.utcnow() + datetime.timedelta(days=7)).isoformat()

    games = []
    rows_for_sheets = []
    source_flag = "unknown"

    try:
        if mode == "historical":
            raise RuntimeError("Force historical mode")

        if allow_api:
            print("[DEBUG] Trying live odds...")
            odds = get_odds(sport, start, end)
            source_flag = "live"
            for ev in odds:
                home = ev.get("home_team")
                away = ev.get("away_team")
                event_id = ev.get("id")
                commence = ev.get("commence_time")

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

            # log rows if needed
            if games:
                log_to_sheets(sport, rows_for_sheets)

    except Exception as e:
        print(f"[WARN] Live odds failed ({e}), falling back to Sheets...")
        rows_for_sheets = read_from_sheets(sport)
        source_flag = "historical (fallback)"
        if rows_for_sheets:
            df = pd.DataFrame(rows_for_sheets)
            for event_id, group in df.groupby("event_id"):
                game = {
                    "home_team": group["home"].iloc[0],
                    "away_team": group["away"].iloc[0],
                    "commence_time": group["commence_time"].iloc[0],
                    "books": {},
                    "summary": {}
                }
                games.append(game)

    payload = {
        "status": "success",
        "week": week,
        "games": games,
        "source": source_flag,   # 🔥 live / historical / fallback
        "survivor": {
            "used": [],
            "week": week
        }
    }
    return payload

# -------------------------
# Excel Export (with source flag)
# -------------------------

def to_excel(payload):
    """Return Excel bytes from payload."""
    games = payload.get("games", [])
    df = pd.DataFrame(games)
    output = pd.ExcelWriter("output.xlsx", engine="xlsxwriter")

    # Games
    df.to_excel(output, index=False, sheet_name="games")

    # Survivor
    survivor_df = pd.DataFrame([payload.get("survivor", {})])
    survivor_df.to_excel(output, index=False, sheet_name="survivor")

    # Metadata / source flag
    meta_df = pd.DataFrame([{"data_source": payload.get("source", "unknown")}])
    meta_df.to_excel(output, index=False, sheet_name="metadata")

    output.close()
    with open("output.xlsx", "rb") as f:
        return f.read()
