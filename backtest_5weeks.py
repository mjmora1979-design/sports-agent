"""
backtest_5weeks.py
-------------------
Runs multi-week backtests (Weeks 1–5) using Monte Carlo model outputs.
Now includes smarter team normalization and full calibration logging.
"""

import pandas as pd
from datetime import datetime
import os, time
from monte_carlo_model import run_monte_carlo, calibrate_model


def normalize_team(name):
    """Normalize team names to allow fuzzy matching between data sources."""
    if not isinstance(name, str):
        return ""
    name = name.lower().replace(".", "").replace(" ", "")
    replacements = {
        "nyjets": "jets",
        "newyorkjets": "jets",
        "nygiants": "giants",
        "newyorkgiants": "giants",
        "laf": "rams",
        "larams": "rams",
        "lasvegasraiders": "raiders",
        "oaklandraiders": "raiders",
        "sdchargers": "chargers",
        "lachargers": "chargers",
        "kansascitychiefs": "chiefs",
        "kcchiefs": "chiefs",
        "nepatriots": "patriots",
        "nenglandpatriots": "patriots",
    }
    for key, val in replacements.items():
        if key in name:
            return val
    return name


def run_backtest(weeks=5):
    print(f"[INFO] Running back-test for Weeks 1–{weeks}\n")

    all_calibrations = []

    for week in range(1, weeks + 1):
        print(f"===== WEEK {week} =====")
        try:
            df, plays_df = run_monte_carlo(snapshot_type="opening", n_sims=20000, sim_confidence=0.8)

            # Save week-specific sim output
            df.to_csv(f"sim_output_week{week}.csv", index=False)
            plays_df.to_csv(f"value_opportunities_week{week}.csv", index=False)

            # Run calibration on this week's sim
            calib = calibrate_model(df)
            if calib is not None and not calib.empty:
                calib["week"] = week
                all_calibrations.append(calib)
            else:
                print(f"[WARN] No overlapping matchups for Week {week}")

            time.sleep(1)

        except Exception as e:
            print(f"[ERROR] Week {week}: {e}")
            continue

    # Combine and log all calibrations
    if all_calibrations:
        combined = pd.concat(all_calibrations, ignore_index=True)
        combined.to_csv("week_calibration.csv", index=False)
        print("\n✅ Back-test complete → week_calibration.csv")

        summary = combined.groupby("week")["correct"].mean() * 100
        print("\n📈 Summary:")
        print(summary)
    else:
        print("\n⚠️ No calibration data generated — check team normalization or final_scores.csv formatting.")


if __name__ == "__main__":
    run_backtest(weeks=5)
