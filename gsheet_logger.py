import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# === CONFIG ===
SHEET_ID = "1-c4BMXcV_0cXl2yFNBUygUSiLeHRyKPYQQIo32IStek"  # e.g., 1WF0NB9fnxhDPEi_arGSp18Kev9KXdoX-IePIE8KJgCQ
WORKSHEET_NAME = "Sportsdata"          # This is your tab name
CREDENTIALS_FILE = "credentials.json"

def get_sheet():
    scope = ["https://spreadsheets.google.com/feeds",
             "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).worksheet(WORKSHEET_NAME)
    return sheet

def log_to_sheets(data, sheet_name=WORKSHEET_NAME):
    sheet = get_sheet()
    if isinstance(data, dict):
        row = [datetime.utcnow().isoformat()] + [str(v) for v in data.values()]
        sheet.append_row(row)
        print(f"[OK] Logged dict with {len(data)} items to {sheet_name}")
    elif isinstance(data, list):
        for item in data:
            row = [datetime.utcnow().isoformat()] + [str(v) for v in item.values()]
            sheet.append_row(row)
        print(f"[OK] Logged {len(data)} records to {sheet_name}")
    else:
        sheet.append_row([datetime.utcnow().isoformat(), str(data)])
        print("[OK] Logged single item to sheet")

if __name__ == "__main__":
    try:
        sheet = get_sheet()
        print(f"[OK] Connected to Google Sheet '{SHEET_ID}', tab '{WORKSHEET_NAME}'")
        sheet.append_row(["Test", "Connection", datetime.utcnow().isoformat()])
        print("[OK] Test row added successfully.")
    except Exception as e:
        print("[ERROR] Could not connect to Google Sheet:", e)
