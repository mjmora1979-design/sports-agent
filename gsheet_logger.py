import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# === CONFIG ===
SHEET_ID = "1-c4BMXcV_0cXl2yFNBUygUSiLeHRyKPYQQIo32IStek"
WORKSHEET_NAME = "Sportsdata"
CREDENTIALS_FILE = "credentials.json"

def get_sheet():
    scope = ["https://spreadsheets.google.com/feeds",
             "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).worksheet(WORKSHEET_NAME)

def log_to_sheets(data):
    sheet = get_sheet()
    timestamp = datetime.utcnow().isoformat()
    if isinstance(data, dict):
        sheet.append_row([timestamp] + [str(v) for v in data.values()])
        print(f"[OK] Logged dict with {len(data)} fields.")
    elif isinstance(data, list):
        for row in data:
            sheet.append_row([timestamp] + [str(v) for v in row.values()])
        print(f"[OK] Logged list with {len(data)} records.")
    else:
        sheet.append_row([timestamp, str(data)])
        print("[OK] Logged single entry.")

# For Render deployment test
if __name__ == "__main__":
    try:
        sheet = get_sheet()
        sheet.append_row(["TEST", "Connection", datetime.utcnow().isoformat()])
        print("[OK] Sheets connection successful.")
    except Exception as e:
        print("[ERROR] Sheets connection failed:", e)
