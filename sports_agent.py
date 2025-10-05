import datetime
import traceback
from sportsbook_api import get_events
from scraper_props import scrape_props_for_sport
from gsheet_logger import log_to_sheets

def build_payload(sport="nfl", props=True, fresh_props=False):
    """
    Builds the full payload:
     - events + markets from API
     - props / injuries scraped
     - logs to sheet
    """
    result = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "sport": sport,
        "events": [],
        "props": [],
        "status": "ok"
    }

    # Step 1: pull events + markets
    try:
        ev = get_events(sport)
        result["events"] = ev.get("events", [])
    except Exception as e:
        print(f"[ERROR] get_events failed: {traceback.format_exc()}")
        result["status"] = "error_events"

    # Step 2: scrape props/injuries if requested
    if props:
        try:
            prop_list = scrape_props_for_sport(sport, fresh=fresh_props)
            result["props"] = prop_list
        except Exception as e:
            print(f"[WARN] scrape_props_for_sport failed: {traceback.format_exc()}")

    # Step 3: log to Google Sheets
    try:
        log_to_sheets(sport, result["events"], result["props"])
    except Exception as e:
        print(f"[WARN] log_to_sheets failed: {e}")

    result["event_count"] = len(result["events"])
    result["prop_count"] = len(result["props"])
    return result
