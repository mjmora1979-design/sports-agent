import os
import gspread
from google.oauth2.service_account import Credentials

def log_to_sheets(sheet_name, rows):
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path or not os.path.exists(creds_path):
        print(f"[ERROR] GOOGLE_APPLICATION_CREDENTIALS not found at {creds_path}")
        return

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    client = gspread.authorize(creds)

    sheet_id = os.getenv("GSHEET_ID")
    if not sheet_id:
        print("[ERROR] GSHEET_ID not set")
        return

    sh = client.open_by_key(sheet_id)

    try:
        ws = sh.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=sheet_name, rows="1000", cols="20")

    if rows:
        header = list(rows[0].keys())
        if not ws.get_all_values():  # add header if sheet is empty
            ws.append_row(header)
        for row in rows:
            ws.append_row([row.get(col, "") for col in header])
