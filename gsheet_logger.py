import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SHEET_ID = "1-c4BMXcV_0cXl2yFNBUygUSiLeHRyKPYQQIo32IStek"  # fill in
CREDS_FILE = "credentials.json"

def log_to_sheets(sport, events, props):
    creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).worksheet("SportsData")

    rows = []
    # log events
    for ev in events:
        rows.append([sport, "event", ev.get("name"), ev.get("startTime"), ""])
    # log props
    for pr in props:
        rows.append([sport, "prop", pr.get("player"), pr.get("stat"), str(pr.get("line"))])

    sheet.append_rows(rows, value_input_option="RAW")
