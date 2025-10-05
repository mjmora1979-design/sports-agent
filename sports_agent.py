import datetime
from sportsbook_api import get_events
from prop_scraper import get_nfl_props
from gsheet_logger import log_to_sheets

def build_payload(sport="nfl", props=True, allow_api=True):
    """
    Core data builder — merges event data + scraped props, logs to Sheets
    """
    print(f"[DEBUG] build_payload(sport={sport}, props={props}, allow_api={allow_api})")
    payload = {"timestamp": datetime.datetime.utcnow().isoformat(), "sport": sport, "events": []}

    # --- Step 1: Get event data ---
    events = []
    if allow_api:
        api_data = get_events(sport)
        events = api_data.get("events", [])
        print(f"[OK] Retrieved {len(events)} {sport} events from API")

    # --- Step 2: Scrape props if applicable ---
    props_data = []
    if sport == "nfl" and props:
        props_data = get_nfl_props()
        print(f"[OK] Retrieved {len(props_data)} props from scraper")

    payload["events"] = events
    payload["props"] = props_data

    # --- Step 3: Log to Google Sheets ---
    try:
        log_to_sheets(sport, events, props_data)
        print("[SHEETS] Logged successfully")
    except Exception as e:
        print(f"[WARN] Google Sheets logging failed: {e}")

    payload["status"] = "success"
    payload["event_count"] = len(events)
    payload["prop_count"] = len(props_data)
    return payload
