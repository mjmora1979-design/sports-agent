import os
import requests
import pandas as pd
import datetime as dt
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ============ CONFIG ============
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")  # Your RapidAPI key for sportsbookapi
SPORTSBOOK_HOST = "sportsbook-api2.p.rapidapi.com"
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")  # Your Google Sheet ID
SERVICE_ACCOUNT_FILE = "service_account.json"  # Uploaded to Render

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Default books to keep (can be swapped)
DEFAULT_BOOKS = ["DraftKings", "FanDuel", "Bet365"]

# Cache memory
_odds_cache = {"timestamp": None, "data": None}


# ============ HELPERS ============
def get_sheets_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build("sheets", "v4", credentials=creds)


def ensure_headers():
    """Make sure headers exist in Google Sheet."""
    service = get_sheets_service()
    sheet = service.spreadsheets()
    result = sheet.values().get(
        spreadsheetId=GOOGLE_SHEET_ID, range="Sheet1!A1:H1"
    ).execute()

    values = result.get("values", [])
    if not values:  # Sheet is empty, write headers
        headers = [["Date", "Home Team", "Away Team", "Market", "Name", "Price", "Book", "Snapshot"]]
        sheet.values().update(
            spreadsheetId=GOOGLE_SHEET_ID,
            range="Sheet1!A1",
            valueInputOption="RAW",
            body={"values": headers}
        ).execute()


def append_to_sheet(rows):
    """Append odds rows to Google Sheet."""
    ensure_headers()
    service = get_sheets_service()
    sheet = service.spreadsheets()

    sheet.values().append(
        spreadsheetId=GOOGLE_SHEET_ID,
        range="Sheet1!A:H",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": rows}
    ).execute()


def fetch_odds_from_api(sport="nfl"):
    url = f"https://{SPORTSBOOK_HOST}/odds/{sport}"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": SPORTSBOOK_HOST,
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


# ============ MAIN MODEL ============
def run_model(
    mode="live",
    allow_api=True,
    survivor=False,
    used=None,
    double_from=13,
    game_filter=None,
    max_games=None,
    sport="nfl",
    include_props=False,
    allowed_books=None
):
    global _odds_cache
    now = dt.datetime.utcnow()

    # Caching: only fetch every 2 hours
    if (
        _odds_cache["timestamp"] is None
        or (now - _odds_cache["timestamp"]).total_seconds() > 7200
    ):
        if allow_api:
            raw_data = fetch_odds_from_api(sport)
            _odds_cache = {"timestamp": now, "data": raw_data}
        else:
            raw_data = []
    else:
        raw_data = _odds_cache["data"]

    report = []
    rows_to_save = []
    allowed_books = allowed_books or DEFAULT_BOOKS

    for game in raw_data.get("events", []):
        home = game.get("home_team")
        away = game.get("away_team")
        commence = game.get("commence_time")

        for book in game.get("bookmakers", []):
            if book["title"] not in allowed_books:
                continue
            for market in book.get("markets", []):
                if market["key"] not in ["h2h", "spreads", "totals"] and not include_props:
                    continue
                for outcome in market.get("outcomes", []):
                    entry = {
                        "home_team": home,
                        "away_team": away,
                        "commence_time": commence,
                        "book": book["title"],
                        "market": market["key"],
                        "name": outcome["name"],
                        "price": outcome["price"],
                    }
                    report.append(entry)

                    # Format row for Sheets
                    rows_to_save.append([
                        now.isoformat(),
                        home,
                        away,
                        market["key"],
                        outcome["name"],
                        outcome["price"],
                        book["title"],
                        f"snapshot_{now.strftime('%Y%m%d%H%M')}"
                    ])

    if rows_to_save:
        append_to_sheet(rows_to_save)

    # Survivor placeholder
    survivor_state = {"week": double_from, "used": used or []}

    return report, [], survivor_state


def save_excel(report, prev, filename, survivor=None):
    df = pd.DataFrame(report)
    df.to_excel(filename, index=False)


def nowstamp():
    return dt.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
