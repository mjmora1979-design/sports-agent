import os
import gspread
from google.oauth2.service_account import Credentials
import datetime

def get_gsheet_client():
    """Authorize and return gspread client using service account JSON from Render secrets."""
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path or not os.path.exists(creds_path):
        raise RuntimeError("Google credentials file not found. Check GOOGLE_APPLICATION_CREDENTIALS.")

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    return gspread.authorize(creds)

def log_to_sheets(sport, rows):
    """Append odds/props rows to Google Sheet if SHEETS_ENABLED is 1."""
    try:
        if os.getenv("SHEETS_ENABLED", "0") != "1":
            print("[INFO] Sheets logging disabled.")
            return

        SHEET_ID = os.getenv("GSHEET_ID")
        if not SHEET_ID:
            print("[ERROR] GSHEET_ID not set in environment.")
            return

        client = get_gsheet_client()
        sheet = client.open_by_key(SHEET_ID).sheet1  # Always write to first sheet for now

        header = list(rows[0].keys()) if rows else []
        if sheet.row_count == 0:
            sheet.append_row(header)

        for row in rows:
            values = [row.get(h, "") for h in header]
            sheet.append_row(values)

        print(f"[INFO] Logged {len(rows)} rows for {sport} to Google Sheets.")
    except Exception as e:
        print("[ERROR] Sheets logging failed:", e)
