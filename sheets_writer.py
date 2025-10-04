import os
import json
import gspread
from google.oauth2.service_account import Credentials

def log_to_sheets(sport, rows):
    """
    Append rows of betting data to Google Sheets.
    rows = list of dicts with fields: timestamp_utc, event_id, commence_time, home, away, book, market, label, price, point_or_line
    """

    try:
        if os.getenv("SHEETS_ENABLED", "0") != "1":
            print("[INFO] Sheets logging skipped (SHEETS_ENABLED != 1)")
            return

        gsheet_id = os.getenv("GSHEET_ID")
        creds_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")

        if not gsheet_id or not creds_json:
            print("[WARN] Sheets logging skipped (missing GSHEET_ID or GOOGLE_SERVICE_ACCOUNT_JSON)")
            return

        # Load service account credentials
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )

        client = gspread.authorize(creds)
        try:
            sheet = client.open_by_key(gsheet_id)
        except Exception as e:
            print("[ERROR] Could not open Google Sheet:", e)
            return

        # Use sport-specific tab, fallback to "logs"
        try:
            worksheet = sheet.worksheet(sport)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sheet.add_worksheet(title=sport, rows="1000", cols="20")

        headers = [
            "timestamp_utc", "event_id", "commence_time",
            "home", "away", "book", "market", "label",
            "price", "point_or_line"
        ]

        # Add header if new sheet
        if not worksheet.row_values(1):
            worksheet.append_row(headers, value_input_option="USER_ENTERED")

        # Flatten dict rows into list rows
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

        worksheet.append_rows(values, value_input_option="USER_ENTERED")
        print(f"[INFO] Logged {len(values)} rows to Google Sheet: {sport}")

    except Exception as e:
        print("[ERROR] Sheets logging failed:", e)
