"""
save_weekly_odds.py
-------------------
Captures current NFL odds snapshot (opening or closing) for future backtesting.
"""

import json, sys, os
from datetime import datetime
from sports_agent import build_payload

def save_current_week_odds(week_number: int, season=2025, snapshot_type="opening"):
    """Fetch and save current odds for a given week."""
    raw_json = build_payload("nfl", snapshot_type)
    os.makedirs("data/historical_odds", exist_ok=True)
    filename = f"data/historical_odds/{season}_week{week_number}_{snapshot_type}.json"
    with open(filename, "w") as f:
        json.dump(raw_json, f, indent=2)
    print(f"✅ Saved {snapshot_type} odds for Week {week_number} → {filename}")

if __name__ == "__main__":
    week = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    snapshot = sys.argv[2] if len(sys.argv) > 2 else "opening"
    save_current_week_odds(week, snapshot_type=snapshot)
