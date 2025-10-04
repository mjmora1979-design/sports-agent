import os
import json
import gspread
from google.oauth2.service_account import Credentials

# -------------------------
# Google Sheets Setup
# -------------------------

def get_sheets_client():
    """Authenticate with Google Sheets using JSON from environment variable."""
    creds_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if not creds_json:
        raise RuntimeError("Missing GOOGLE_APPLICATION_CREDENTIALS_JSON in environment")

    try:
        creds_dict = json.loads(creds_json)
    except Exception as e:
        raise RuntimeError(f"Failed to parse GOOGLE_APPLICATION_CREDENTIALS_JSON: {e}")

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client

# -------------------------
# Log to Sheets
# -------------------------

def log_to_sheets(sport, rows):
    """Append odds data to Google Sheet if SHEETS_ENABLED=1."""
    if os.getenv("SHEETS_ENABLED", "0") != "1":
        print("[DEBUG] Sheets logging disabled.")
        return

    sheet_id = os.getenv("GSHEET_ID")
    if not sheet_id:
        print("[ERROR] GSHEET_ID is not set in environment")
        return

    try:
        client = get_sheets_client()
        sheet = client.open_by_key(sheet_id)
        try:
            worksheet = sheet.worksheet(sport)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sheet.add_worksheet(title=sport, rows="1000", cols="20")

        headers = [
            "timestamp_utc",
            "event_id",
            "commence_time",
            "home",
            "away",
            "book",
            "market",
            "label",
            "price",
            "point_or_line"
        ]

        # Add headers if first row empty
        if not worksheet.get_all_values():
            worksheet.append_row(headers)

        # Append each row
        values = [[
            r.get("timestamp_utc", ""),
            r.get("event_id", ""),
            r.get("commence_time", ""),
            r.get("home", ""),
            r.get("away", ""),
            r.get("book", ""),
            r.get("market", ""),
            r.get("label", ""),
            r.get("price", ""),
            r.get("point_or_line", "")
        ] for r in rows]

        worksheet.append_rows(values)
        print(f"[INFO] Logged {len(values)} rows to {sport} sheet.")

    except Exception as e:
        print(f"[ERROR] Sheets logging failed: {e}")
