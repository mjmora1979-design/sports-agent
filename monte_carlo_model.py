"""
monte_carlo_model.py
--------------------
Runs Monte Carlo simulations using model-adjusted probabilities
from model_payload.build_model_payload().

Simulates N games to estimate expected value (EV) and Kelly-lite stake size.
Adds calibration persistence: save_calibration(), load_calibration(), apply_calibration()
so the model can learn biases and use them on future runs.
"""

import numpy as np
import pandas as pd
from datetime import datetime
import os, json
from model_payload import build_model_payload
from sports_agent import build_payload


# ==============================
# Calibration persistence
# ==============================
CALIB_PATH = "calibrated_params.json"

def save_calibration(params: dict, filename: str = CALIB_PATH):
    """Save calibration parameters to disk."""
    try:
        with open(filename, "w") as f:
            json.dump(params, f, indent=2)
        print(f"[CALIB] Saved calibration → {filename}")
    except Exception as e:
        print(f"[CALIB] Failed to save: {e}")

def load_calibration(filename: str = CALIB_PATH):
    """Load calibration parameters if present."""
    if not os.path.exists(filename):
        print(f"[CALIB] No calibration file at {filename} (using defaults).")
        return None
    try:
        with open(filename, "r") as f:
            params = json.load(f)
        print(f"[CALIB] Loaded calibration from {filename}")
        return params
    except Exception as e:
        print(f"[CALIB] Failed to load: {e}")
        return None

def apply_calibration(home_prob: float, away_prob: float, calib: dict | None):
    """
    Apply persisted calibration to fair probabilities, then re-normalize.
    Supported keys (all optional):
      - home_bias_mult (default 1.0)
      - away_bias_mult (default 1.0)
      - favorite_bias_mult (default 1.0)  # boosts favored side
    """
    if calib is None:
        return home_prob, away_prob

    hp = float(home_prob)
    ap = float(away_prob)

    home_mult = float(calib.get("home_bias_mult", 1.0))
    away_mult = float(calib.get("away_bias_mult", 1.0))
    fav_mult  = float(calib.get("favorite_bias_mult", 1.0))

    # baseline home/away
    hp *= home_mult
    ap *= away_mult

    # favorite boost: slightly increase the larger side
    if hp > ap:
        hp *= fav_mult
    elif ap > hp:
        ap *= fav_mult

    # re-normalize to sum to 1
    total = hp + ap
    if total <= 0:
        # fallback: equal probs
        hp, ap = 0.5, 0.5
    else:
        hp /= total
        ap /= total

    return hp, ap


# ==============================
# Core Monte Carlo simulation
# ==============================
def simulate_matchup(home_prob: float, away_prob: float, n_sims: int = 20000):
    """Simulate N games using adjusted win probabilities."""
    if np.isnan(home_prob) or np.isnan(away_prob):
        return np.nan, np.nan, np.nan

    draws = np.random.rand(n_sims)
    home_wins = np.sum(draws < home_prob)
    away_wins = n_sims - home_wins

    home_win_pct = home_wins / n_sims
    away_win_pct = away_wins / n_sims
    std_error = np.sqrt(home_prob * (1 - home_prob) / n_sims)
    return home_win_pct, away_win_pct, std_error


def kelly_fraction(edge: float, odds: float, fraction_cap: float = 0.25):
    """Compute 'Kelly-lite' staking fraction based on EV edge."""
    try:
        b = abs(odds) / 100 if odds < 0 else odds / 100
        q = 1 - (1 / (b + 1))
        kelly = ((b * (edge / 100)) - q) / b
        return max(0, min(kelly, fraction_cap))
    except Exception:
        return 0.0


# ==============================
# Simulation runner
# ==============================
def run_monte_carlo(snapshot_type="opening", n_sims=20000, sim_confidence=0.8, calibration: dict | None = None):
    """
    Builds model payload, applies calibration (if any), runs Monte Carlo simulations,
    and returns both matchup-level and team-level datasets.
    """
    print(f"[INFO] Running Monte Carlo: {snapshot_type} ({n_sims:,} sims per matchup)")

    # Build data payload (current odds snapshot)
    raw_json = build_payload("nfl", snapshot_type)
    model_df = build_model_payload(raw_json, snapshot_type=snapshot_type, sim_confidence=sim_confidence)

    results = []
    for _, row in model_df.iterrows():
        # 1) start from model fair probs
        home_prob = row["home_fair_prob"]
        away_prob = row["away_fair_prob"]

        # 2) apply persisted calibration (if present)
        home_prob_adj, away_prob_adj = apply_calibration(home_prob, away_prob, calibration)

        # 3) simulate
        home_win_pct, away_win_pct, std_err = simulate_matchup(home_prob_adj, away_prob_adj, n_sims)

        # 4) EV vs market
        home_ev = (home_win_pct - row["home_ml_prob"]) * 100
        away_ev = (away_win_pct - row["away_ml_prob"]) * 100

        # 5) Kelly stake
        home_kelly = kelly_fraction(home_ev, row["home_ml"] if pd.notna(row["home_ml"]) else -110)
        away_kelly = kelly_fraction(away_ev, row["away_ml"] if pd.notna(row["away_ml"]) else -110)

        results.append({
            "bookmaker": row["bookmaker"],
            "home_team": row["home_team"],
            "away_team": row["away_team"],
            "home_ml": row["home_ml"],
            "away_ml": row["away_ml"],
            "home_prob_model": round(home_prob_adj, 4),
            "home_win_sim": round(home_win_pct, 4),
            "home_EV_%": round(home_ev, 2),
            "home_Kelly_frac": round(home_kelly, 3),
            "away_prob_model": round(away_prob_adj, 4),
            "away_win_sim": round(away_win_pct, 4),
            "away_EV_%": round(away_ev, 2),
            "away_Kelly_frac": round(away_kelly, 3),
            "std_error": round(std_err, 5),
            "snapshot_type": snapshot_type,
            "generated_at": datetime.utcnow().isoformat()
        })

    df = pd.DataFrame(results)

    # Create two-sided list
    all_plays = []
    for _, r in df.iterrows():
        all_plays.append({
            "bookmaker": r["bookmaker"],
            "team_side": "Home",
            "team": r["home_team"],
            "opponent": r["away_team"],
            "odds": r["home_ml"],
            "EV_%": r["home_EV_%"],
            "Kelly_frac": r["home_Kelly_frac"]
        })
        all_plays.append({
            "bookmaker": r["bookmaker"],
            "team_side": "Away",
            "team": r["away_team"],
            "opponent": r["home_team"],
            "odds": r["away_ml"],
            "EV_%": r["away_EV_%"],
            "Kelly_frac": r["away_Kelly_frac"]
        })

    plays_df = pd.DataFrame(all_plays)

    # Save outputs
    df.to_csv("sim_output_full.csv", index=False)
    plays_df.to_csv("value_opportunities.csv", index=False)

    # Pretty console log
    top5 = plays_df.sort_values(by="EV_%", ascending=False).head(5)
    print("\n🏈 Top 5 Overall Value Opportunities (by EV %)")
    print(top5[["bookmaker", "team_side", "team", "opponent", "odds", "EV_%", "Kelly_frac"]])
    print("💾 Saved outputs → sim_output_full.csv and value_opportunities.csv")

    return df, plays_df


# ==============================
# Calibration tracker (diagnostic)
# ==============================
def calibrate_model(sim_df: pd.DataFrame, results_path="final_scores.csv"):
    """
    Compare simulated winner vs actual winner. Returns merged df or None.
    NOTE: This function does NOT change parameters by itself.
          Use the summary it creates to derive calibration params and call save_calibration().
    """
    if not os.path.exists(results_path):
        print(f"[WARN] No results file found at {results_path}. Skipping calibration.")
        return None

    actuals = pd.read_csv(results_path)

    def norm(name):
        return str(name).lower().replace(" ", "").replace(".", "")

    # normalize
    actuals["home_team"] = actuals["home_team"].apply(norm)
    actuals["away_team"] = actuals["away_team"].apply(norm)
    sim_df = sim_df.copy()
    sim_df["home_team"] = sim_df["home_team"].apply(norm)
    sim_df["away_team"] = sim_df["away_team"].apply(norm)

    merged = pd.merge(sim_df, actuals, on=["home_team", "away_team"], how="inner")
    if merged.empty:
        print("[WARN] No overlapping matchups found after normalization.")
        return None

    merged["predicted_winner"] = np.where(
        merged["home_win_sim"] > merged["away_win_sim"],
        merged["home_team"],
        merged["away_team"]
    )
    merged["correct"] = merged["predicted_winner"] == merged["winner"].apply(norm)

    accuracy = merged["correct"].mean() * 100
    print(f"\n📈 Model Calibration Accuracy: {accuracy:.2f}% on {len(merged)} games")

    merged["evaluated_at"] = datetime.utcnow().isoformat()
    merged.to_csv("calibration_log.csv", index=False)
    print("✅ Calibration log saved → calibration_log.csv")
    return merged


# ==============================
# Local test
# ==============================
if __name__ == "__main__":
    # Load calibration if present and run a test
    calib = load_calibration()
    df, plays_df = run_monte_carlo(snapshot_type="opening", n_sims=20000, sim_confidence=0.8, calibration=calib)
    print("\n✅ Monte Carlo run complete — sample output:")
    print(df.head())
    calibrate_model(df)
