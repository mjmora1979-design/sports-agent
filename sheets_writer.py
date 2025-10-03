import os, json, base64, datetime
import gspread

# Cache client to avoid reconnect every call
_client = None

def get_client():
    """Return a gspread client using Service Account JSON from env."""
    global _client
    if _client:
        return _client

    sa_json = os.getenv("GOOGLE_SA_JSON")
    if not sa_json:
        raise RuntimeError("GOOGLE_SA_JSON not set")

    try:
        # Try direct JSON first
        creds = json.loads(sa_json)
    except json.JSONDecodeError:
        # If base64 encoded, decode and load
        creds = json.loads(base64.b64decode(sa_json).decode("utf-8"))

    _client = gspread.service_account_from_dict(creds)
    return _client

def log_to_sheets(sport, rows):
    """
    Append betting odds rows into Google Sheet.
    - sport: string like 'nfl'
    - rows: list of dicts with keys:
        timestamp_utc, event_id, commence_time, home, away,
        book, market, label, price, point_or_line
    """
    if os.getenv("SHEETS_ENABLED", "0") != "1":
        print("[DEBUG] Sheets logging skipped (SHEETS_ENABLED=0).")
        return

    gsheet_id = os.getenv("GSHEET_ID")
    if not gsheet_id:
        print("[DEBUG] GSHEET_ID not set, skipping log.")
        return

    try:
        client = get_client()
        sh = client.open_by_key(gsheet_id)
        tab_name = f"{sport}_log"

        # Ensure worksheet exists
        try:
            ws = sh.worksheet(tab_name)
        except gspread.exceptions.WorksheetNotFound:
            ws = sh.add_worksheet(title=tab_name, rows=1000, cols=10)
            ws.append_row([
                "timestamp_utc","event_id","commence_time","home","away",
                "book","market","label","price","point_or_line"
            ])

        values = []
        for r in rows:
            values.append([
                r.get("timestamp_utc", datetime.datetime.utcnow().isoformat() + "Z"),
                r.get("event_id",""),
                r.get("commence_time",""),
                r.get("home",""),
                r.get("away",""),
                r.get("book",""),
                r.get("market",""),
                r.get("label",""),
                r.get("price",""),
                r.get("point_or_line","")
            ])

        if values:
            ws.append_rows(values, value_input_option="USER_ENTERED")
            print(f"[DEBUG] Logged {len(values)} rows to tab '{tab_name}'")

    except Exception as e:
        print(f"[ERROR] Sheets logging failed: {e}")
