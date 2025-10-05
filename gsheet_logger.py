import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SHEET_ID = "YOUR_GOOGLE_SHEET_ID_HERE"  # Replace with your Sheet ID
CREDS_FILE = "credentials.json"  # Make sure this is deployed to Render

def log_to_sheets(sport, events, props):
    """Appends summary rows to a Google Sheet for backtesting & monitoring"""
    creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).worksheet("SportsData")

    rows = []
    for ev in events:
        rows.append([
            sport,
            ev.get("name"),
            ev.get("startTime"),
            "event",
            ""
        ])
    for pr in props:
        rows.append([
            sport,
            pr.get("player"),
            pr.get("stat"),
            "prop",
            pr.get("line")
        ])

    sheet.append_rows(rows, value_input_option="RAW")
