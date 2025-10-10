"""
model_payload.py
----------------
Transforms live odds JSON (from your /odds endpoint)
into a calibrated model payload with implied probabilities,
dynamic haircuts, and market edge calculations.

This version supports future Monte Carlo integration
through the calibrated_haircut() function.
"""

import pandas as pd
import numpy as np
from datetime import datetime


# ------------------------------------------------------------
# Utility: Convert American odds to implied probability
# ------------------------------------------------------------
def american_to_prob(odds):
    """Convert American odds (+110 / -150) to implied probability."""
    try:
        odds = float(odds)
        if odds > 0:
            return 100 / (odds + 100)
        else:
            return -odds / (-odds + 100)
    except Exception:
        return np.nan


# ------------------------------------------------------------
# Dynamic Haircut System
# ------------------------------------------------------------
def calibrated_haircut(
    prob: float,
    snapshot_type: str = "opening",
    injury_flag: bool = False,
    sim_confidence: float = 0.8,
):
    """
    Hybrid haircut system:
      - Adjusts conservatism by market timing (opening/closing)
      - Adds injury penalty if applicable
      - Scales by simulation confidence (0–1)

    The higher the simulation confidence, the less haircut applied.
    """
    if np.isnan(prob) or prob <= 0:
        return np.nan

    # --- Base haircut by timing ---
    if snapshot_type == "opening":
        base = 0.20  # early week
    elif snapshot_type == "closing":
        base = 0.10  # sharper lines
    else:
        base = 0.15  # default midweek

    # --- Adjust for injuries ---
    if injury_flag:
        base += 0.05

    # --- Scale by model confidence ---
    # e.g. 0.8 confidence → reduces haircut by 20%
    adj = base * (1 - sim_confidence)

    adjusted_prob = prob * (1 - adj)
    return adjusted_prob


# ------------------------------------------------------------
# Flatten JSON odds data
# ------------------------------------------------------------
def flatten_odds(json_data):
    """
    Flatten the nested /odds JSON payload into a clean DataFrame.

    Expected structure from sports_agent.build_payload():
      - json_data["games"] list of matchups
      - each game has bookmakers -> markets -> prices
    """
    games = json_data.get("games", [])
    rows = []

    for g in games:
        home = g.get("home_team")
        away = g.get("away_team")
        for book in g.get("bookmakers", []):
            site = book.get("bookmaker")
            markets = book.get("markets", {})

            ml = markets.get("h2h", {})
            home_ml = ml.get(home, {}).get("price") if ml else None
            away_ml = ml.get(away, {}).get("price") if ml else None

            row = {
                "snapshot_type": json_data.get("snapshot_type", "opening"),
                "timestamp_utc": json_data.get("timestamp_utc", datetime.utcnow().isoformat()),
                "bookmaker": site,
                "home_team": home,
                "away_team": away,
                "home_ml": home_ml,
                "away_ml": away_ml,
                "home_ml_prob": american_to_prob(home_ml),
                "away_ml_prob": american_to_prob(away_ml),
            }
            rows.append(row)

    return pd.DataFrame(rows)


# ------------------------------------------------------------
# Core model payload builder
# ------------------------------------------------------------
def build_model_payload(
    json_data,
    snapshot_type="opening",
    injury_flags=None,
    sim_confidence=0.8,
):
    """
    Converts raw odds data into model-adjusted probabilities and fair odds.

    Args:
        json_data (dict): Raw odds from /odds endpoint
        snapshot_type (str): "opening" or "closing"
        injury_flags (dict): optional {team_name: bool} map
        sim_confidence (float): model confidence (0–1)
    """
    df = flatten_odds(json_data)
    injury_flags = injury_flags or {}

    df["home_injury_flag"] = df["home_team"].map(lambda t: injury_flags.get(t, False))
    df["away_injury_flag"] = df["away_team"].map(lambda t: injury_flags.get(t, False))

    df["home_adj_prob"] = df.apply(
        lambda r: calibrated_haircut(
            r["home_ml_prob"],
            snapshot_type=r.get("snapshot_type", snapshot_type),
            injury_flag=r["home_injury_flag"],
            sim_confidence=sim_confidence,
        ),
        axis=1,
    )

    df["away_adj_prob"] = df.apply(
        lambda r: calibrated_haircut(
            r["away_ml_prob"],
            snapshot_type=r.get("snapshot_type", snapshot_type),
            injury_flag=r["away_injury_flag"],
            sim_confidence=sim_confidence,
        ),
        axis=1,
    )

    # Normalize to 1.0 for fair probability set
    df["prob_sum"] = df["home_adj_prob"] + df["away_adj_prob"]
    df["home_fair_prob"] = df["home_adj_prob"] / df["prob_sum"]
    df["away_fair_prob"] = df["away_adj_prob"] / df["prob_sum"]

    # Convert fair probs back to “fair” odds
    df["home_fair_odds"] = np.where(
        df["home_fair_prob"] > 0,
        -100 * df["home_fair_prob"] / (1 - df["home_fair_prob"]),
        np.nan,
    )
    df["away_fair_odds"] = np.where(
        df["away_fair_prob"] > 0,
        -100 * df["away_fair_prob"] / (1 - df["away_fair_prob"]),
        np.nan,
    )

    # Calculate model edge (% difference vs. market)
    df["model_edge_home_%"] = (df["home_ml_prob"] - df["home_fair_prob"]) * 100
    df["model_edge_away_%"] = (df["away_ml_prob"] - df["away_fair_prob"]) * 100

    df["generated_at"] = datetime.utcnow().isoformat()

    return df


# ------------------------------------------------------------
# Quick test (local only)
# ------------------------------------------------------------
if __name__ == "__main__":
    from sports_agent import build_payload

    # Test using NFL odds (opening snapshot)
    sample = build_payload("nfl", "opening")
    result = build_model_payload(sample, snapshot_type="opening", sim_confidence=0.8)
    print(result.head())
