"""
backtest_5weeks.py
-------------------
Runs historical multi-week backtest using stored JSON odds snapshots.
"""

import json, os, pandas as pd, time
from monte_carlo_model import run_monte_carlo, calibrate_model
from model_payload import build_model_payload

def load_historical_week(week, season=2025, snapshot_type="opening"):
    """Load saved historical odds snapshot."""
    path = f"data/historical_odds/{season}_week{week}_{snapshot_type}.json"
    if not os.path.exists(path):
        raise FileNotFoundError(f"❌ Missing {path}")
    with open(path, "r") as f:
        return json.load(f)

def run_historical_backtest(weeks=[1,2,3,4,5], season=2025):
    print(f"[INFO] Running historical backtest for {season} Weeks {weeks[0]}–{weeks[-1]}")

    all_calibrations = []

    for week in weeks:
        print(f"\n===== WEEK {week} =====")
        try:
            # Load that week's saved odds JSON
            raw_json = load_historical_week(week, season)
            model_df = build_model_payload(raw_json, snapshot_type="opening")
            # Run simulation directly on that dataframe
            from monte_carlo_model import simulate_matchup, kelly_fraction
            results = []
            for _, r in model_df.iterrows():
                home_win_sim, away_win_sim, se = simulate_matchup(r["home_fair_prob"], r["away_fair_prob"])
                home_ev = (home_win_sim - r["home_ml_prob"]) * 100
                away_ev = (away_win_sim - r["away_ml_prob"]) * 100
                home_kelly = kelly_fraction(home_ev, r["home_ml"])
                away_kelly = kelly_fraction(away_ev, r["away_ml"])
                results.append({
                    "home_team": r["home_team"],
                    "away_team": r["away_team"],
                    "home_win_sim": home_win_sim,
                    "away_win_sim": away_win_sim,
                    "home_EV_%": home_ev,
                    "away_EV_%": away_ev,
                    "home_Kelly_frac": home_kelly,
                    "away_Kelly_frac": away_kelly,
                    "bookmaker": r["bookmaker"]
                })

            week_df = pd.DataFrame(results)
            week_df.to_csv(f"sim_output_week{week}.csv", index=False)

            # Calibrate against real results
            calib = calibrate_model(week_df)
            if calib is not None and not calib.empty:
                calib["week"] = week
                all_calibrations.append(calib)
            else:
                print(f"[WARN] No overlapping matchups for Week {week}")
            time.sleep(1)
        except Exception as e:
            print(f"[ERROR] Week {week}: {e}")

    if all_calibrations:
        combined = pd.concat(all_calibrations, ignore_index=True)
        combined.to_csv("week_calibration.csv", index=False)
        print("\n✅ Backtest complete → week_calibration.csv")
        print(combined.groupby("week")["correct"].mean() * 100)
    else:
        print("\n⚠️ No calibration data generated — likely missing or mismatched odds/results.")

if __name__ == "__main__":
    run_historical_backtest([1,2,3,4,5])
