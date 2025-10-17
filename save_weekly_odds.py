"""
save_weekly_odds.py
-------------------
Captures current NFL odds snapshots (opening/closing) each week for backtesting.
Run this manually once or twice per week:
    python3 save_weekly_odds.py 7 opening
    python3 save_weekly_odds.py 7 closing
"""

import json
import os
import sys
from datetime import datetime
from sports_agent import build_payload

DATA_DIR = "data/historical_odds"

def save_current_week_odds(week_number: int, snapshot_type: str = "opening", season: int = 2025):
    """Fetch current odds snapshot from Sportsbook API and save it for backtesting."""
    os.makedirs(DATA_DIR, exist_ok=True)

    # Build payload with the model’s own odds-fetching logic
    raw_json = build_payload("nfl", snapshot_type)

    filename = f"{DATA_DIR}/{season}_week{week_number}_{snapshot_type}.json"
    with open(filename, "w") as f:
        json.dump(raw_json, f, indent=2)

    print(f"✅ Saved {snapshot_type} odds for Week {week_number} → {filename}")
    print(f"Games saved: {len(raw_json) if isinstance(raw_json, list) else 'unknown'}")

if __name__ == "__main__":
    # Default args: week=7, snapshot_type='opening', season=2025
    week = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    snapshot = sys.argv[2] if len(sys.argv) > 2 else "opening"
    season = int(sys.argv[3]) if len(sys.argv) > 3 else 2025

    save_current_week_odds(week, snapshot_type=snapshot, season=season)
