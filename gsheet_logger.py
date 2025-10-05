import os, json, gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

SHEET_ID = "1-c4BMXcV_0cXl2yFNBUygUSiLeHRyKPYQQIo32IStek"
WORKSHEET_NAME = "Sportsdata"

def get_creds():
    """Loads credentials from either environment variable or local file."""
    if os.path.exists("credentials.json"):
        with open("credentials.json", "r") as f:
            return json.load(f)
    elif os.getenv("GOOGLE_CREDS_JSON"):
        return json.loads(os.getenv("GOOGLE_CREDS_JSON"))
    else:
        raise FileNotFoundError("No credentials.json file or GOOGLE_CREDS_JSON env var found.")

def get_sheet():
    scope = ["https://spreadsheets.google.com/feeds",
             "https://www.googleapis.com/auth/drive"]
    creds_dict = get_creds()
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).worksheet(WORKSHEET_NAME)

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
