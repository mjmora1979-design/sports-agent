# backtest_5weeks.py
"""
Automates 5-week back-testing for Sports-Agent NFL EV model.
Creates week_calibration.csv summarizing accuracy per week.
"""

import pandas as pd, numpy as np, time, os
from datetime import datetime
from monte_carlo_model import run_monte_carlo, calibrate_model
from scraper_results import fetch_game_results   # if your scraper has a callable function
# If not, you can just run scraper_results.py separately once beforehand

def backtest_last_5_weeks(start_week=1, end_week=5):
    summary_rows = []

    print(f"[INFO] Running back-test for Weeks {start_week}-{end_week}")
    for wk in range(start_week, end_week + 1):
        print(f"\n===== WEEK {wk} =====")
        try:
            df, plays_df = run_monte_carlo(snapshot_type="opening",
                                           n_sims=20000,
                                           sim_confidence=0.8)
            calib = calibrate_model(df)
            if calib is None or calib.empty:
                print(f"[WARN] No overlapping matchups for Week {wk}")
                continue

            acc = round(calib["correct"].mean() * 100, 2)
            summary_rows.append({
                "week": wk,
                "games": len(calib),
                "accuracy_%": acc,
                "evaluated_at": datetime.utcnow().isoformat()
            })

            # Save incremental checkpoint
            pd.DataFrame(summary_rows).to_csv("week_calibration.csv", index=False)
            time.sleep(2)   # gentle delay to stay under Render free-tier CPU window
        except Exception as e:
            print(f"[ERROR] Week {wk}: {e}")

    print("\n✅ Back-test complete → week_calibration.csv")
    return pd.DataFrame(summary_rows)

if __name__ == "__main__":
    results = backtest_last_5_weeks(start_week=1, end_week=5)
    print("\n📈 Summary:")
    print(results)
