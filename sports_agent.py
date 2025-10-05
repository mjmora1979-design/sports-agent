import datetime
from gsheet_logger import log_to_sheets

def build_payload(sport: str, source: str = "model_test", max_games: int = 10):
    """
    Builds a simplified JSON payload representing a sports model data run.
    """
    print(f"[DEBUG] Building payload for {sport} with {max_games} games")
    timestamp = datetime.datetime.utcnow().isoformat()

    payload = {
        "sport": sport,
        "source": source,
        "timestamp": timestamp,
        "games_processed": max_games
    }

    # Log to Google Sheets
    try:
        log_to_sheets(payload)
        print("[OK] Logged payload to Google Sheets")
    except Exception as e:
        print("[ERROR] Failed to log to Sheets:", e)

    return payload
