import os
import requests
import pandas as pd
import datetime as dt
import json
import gspread
from google.oauth2.service_account import Credentials

# === ENVIRONMENT VARS ===
SPORTSBOOK_KEY = os.getenv("SPORTSBOOK_API_KEY")
GOOGLE_CREDS = os.getenv("GOOGLE_CREDENTIALS")

# === GOOGLE SHEETS SETUP ===
if GOOGLE_CREDS:
    creds_dict = json.loads(GOOGLE_CREDS)
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    gs_client = gspread.authorize(creds)
    SHEET_ID = os.getenv("GOOGLE_SHEET_ID")  # you must set this in Render
    sheet = gs_client.open_by_key(SHEET_ID).sheet1
else:
    gs_client, sheet = None, None

# === SUPPORTED SPORTS MAP ===
SPORT_MAP = {
    "nfl": "americanfootball_nfl",
    "ncaaf": "americanfootball_ncaaf",
    "nba": "basketball_nba",
    "mlb": "baseball_mlb"
}

# === API BASE ===
API_BASE = "https://sportsbook-api2.p.rapidapi.com"

HEADERS = {
    "X-RapidAPI-Key": SPORTSBOOK_KEY,
    "X-RapidAPI-Host": "sportsbook-api2.p.rapidapi.com"
}


def fetch_odds(sport="nfl"):
    """Fetch odds for a given sport from Sportsbook API"""
    sport_key = SPORT_MAP.get(sport.lower())
    if not sport_key:
        raise ValueError(f"Unsupported sport: {sport}")

    url = f"{API_BASE}/odds"
    params = {"sport": sport_key}

    resp = requests.get(url, headers=HEADERS, params=params)
    resp.raise_for_status()
    return resp.json()


def parse_report(data, log_full=False):
    """Extract either full odds or just opening/closing per game"""
    report = []
    for event in data.get("events", []):
        home = event.get("home_team")
        away = event.get("away_team")
        commence = event.get("commence_time")
        markets = event.get("markets", [])

        if log_full:
            # dump all
            for m in markets:
                for outcome in m.get("outcomes", []):
                    report.append({
                        "home_team": home,
                        "away_team": away,
                        "commence_time": commence,
                        "market": m.get("key"),
                        "name": outcome.get("name"),
                        "price": outcome.get("price"),
                        "book": m.get("book")
                    })
        else:
            # just opening + closing odds
            for m in markets:
                outcomes = m.get("outcomes", [])
                if not outcomes:
                    continue
                # first and last snapshot if available
                first = outcomes[0]
                last = outcomes[-1]
                report.extend([
                    {
                        "home_team": home,
                        "away_team": away,
                        "commence_time": commence,
                        "market": m.get("key"),
                        "name": first.get("name"),
                        "price": first.get("price"),
                        "book": m.get("book"),
                        "snapshot": "opening"
                    },
                    {
                        "home_team": home,
                        "away_team": away,
                        "commence_time": commence,
                        "market": m.get("key"),
                        "name": last.get("name"),
                        "price": last.get("price"),
                        "book": m.get("book"),
                        "snapshot": "closing"
                    }
                ])
    return report


def write_to_sheets(report):
    """Append odds to Google Sheets"""
    if not sheet:
        return

    rows = []
    for r in report:
        rows.append([
            r.get("commence_time"),
            r.get("home_team"),
            r.get("away_team"),
            r.get("market"),
            r.get("name"),
            r.get("price"),
            r.get("book"),
            r.get("snapshot", "")
        ])
    if rows:
        sheet.append_rows(rows, value_input_option="RAW")


def run_model(sport="nfl", log_full=False, allow_api=True):
    """Main entry point called by Flask"""
    if not allow_api:
        return [], {}, {"week": 0, "used": []}

    data = fetch_odds(sport)
    report = parse_report(data, log_full=log_full)

    # write to Google Sheets
    write_to_sheets(report)

    survivor_info = {"week": 13, "used": []}  # placeholder for survivor logic
    return report, {}, survivor_info


def nowstamp():
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")
