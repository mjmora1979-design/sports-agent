import os
import datetime
import pandas as pd
import nfl_data_py as nfl
from sportsbook_api import get_events, get_odds
from sheets_writer import log_to_sheets


# -------------------------
# Week detection (NFL only)
# -------------------------
def get_current_football_week():
    """Get NFL current week from nfl_data_py schedules (fallback to ISO week)."""
    try:
        year = datetime.date.today().year
        schedule = nfl.import_schedules([year])
        today = datetime.datetime.utcnow().date()
        upcoming = schedule[schedule['gameday'] >= str(today)]
        if not upcoming.empty:
            return int(upcoming.iloc[0]['week'])
        return int(schedule['week'].max())
    except Exception as e:
        print("[WARN] Week detection failed:", e)
        return datetime.date.today().isocalendar()[1]  # fallback ISO week


# -------------------------
# Helpers
# -------------------------
def is_pro_sport(sport: str) -> bool:
    """Return True if sport is professional (has props)."""
    return sport.lower() in ["nfl", "mlb", "nba", "nhl"]

def is_survivor_supported(sport: str) -> bool:
    """Only NFL supports survivor."""
    return sport.lower() == "nfl"


# -------------------------
# Payload builder
# -------------------------
def build_payload(
    sport: str,
    allow_api: bool = False,
    game_filter=None,
    max_games=None,
    force_refresh: bool = False,
    force_direct_odds: bool = False
):
    """
    Main odds + props payload builder.
    - NFL: full week, survivor, props
    - NCAAF/NCAAB: only top games, no props
    - Other pro sports: full odds + props
    """

    sport = sport.lower()
    week = get_current_football_week() if sport == "nfl" else None

    start = datetime.datetime.utcnow().isoformat()
    end = (datetime.datetime.utcnow() + datetime.timedelta(days=7)).isoformat()

    games = []
    rows_for_sheets = []

    if allow_api:
        try:
            # --- PRO SPORTS (NFL, MLB, NBA, NHL) ---
            if is_pro_sport(sport):
                if force_direct_odds:
                    print("[DEBUG] Forcing direct odds pull...")
                    odds = get_odds(sport)
                else:
                    try:
                        print("[DEBUG] Trying events+odds pull...")
                        events = get_events(sport, start, end)
                        odds = get_odds(sport, events=events)
                    except Exception as e:
                        print(f"[WARN] events+odds failed, fallback to direct odds: {e}")
                        odds = get_odds(sport)

            # --- COLLEGE SPORTS (NCAAF, NCAAB) ---
            else:
                print("[DEBUG] Pulling odds for college sport (no props, top games only)...")
                events = get_events(sport, start, end)
                odds = get_odds(sport, events=events, limit_top=True)

            # --- Normalize game results ---
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
                        # Props only if pro sport
                        "props": data.get("props", {}) if is_pro_sport(sport) else {}
                    }

                game = {
                    "home_team": home,
                    "away_team": away,
                    "commence_time": commence,
                    "books": books,
                    "event_id": event_id
                }
                games.append(game)

                # Flatten into rows for Sheets
                for book, data in books.items():
                    # moneylines
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
                            "point_or_line": "",
                            "source": "api"
                        })
                    # spreads
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
                            "point_or_line": spread.get("point"),
                            "source": "api"
                        })
                    # totals
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
                            "point_or_line": val.get("point"),
                            "source": "api"
                        })
                    # props (only for pro sports)
                    if is_pro_sport(sport):
                        for prop_name, players in data.get("props", {}).items():
                            for player, lines in players.items():
                                for side, line in lines.items():
                                    rows_for_sheets.append({
                                        "timestamp_utc": datetime.datetime.utcnow().isoformat() + "Z",
                                        "event_id": event_id,
                                        "commence_time": commence,
                                        "home": home,
                                        "away": away,
                                        "book": book,
                                        "market": prop_name,
                                        "label": f"{player} {side}",
                                        "price": line.get("price"),
                                        "point_or_line": line.get("point"),
                                        "source": "api"
                                    })

        except Exception as e:
            print(f"[ERROR] build_payload failed: {e}")

    # ✅ Write to Sheets if enabled
    if rows_for_sheets:
        log_to_sheets(sport, rows_for_sheets)

    # Final payload
    payload = {
        "status": "success",
        "week": week,
        "games": games,
        "survivor": {
            "used": [],
            "week": week
        } if is_survivor_supported(sport) else {}
    }
    return payload


# -------------------------
# Excel Export
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
