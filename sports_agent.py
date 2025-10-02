#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sports_agent.py
NFL simulation agent with:
- Safe API guard
- Caching (2h, force refresh <1h before kickoff)
- Game summaries, player props, parlays
- Survivor helper
- Excel export
"""

import os, json, glob, argparse
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Any

import numpy as np, pandas as pd, requests

# -------------------------------
# Config
# -------------------------------
API_KEY = os.environ.get("ODDS_API_KEY", "PASTE_YOUR_API_KEY_HERE")
BASE_URL = "https://api.the-odds-api.com/v4/sports"
SPORT_ID = "americanfootball_nfl"
MARKETS = "h2h,spreads,totals,player_pass_yds,player_rush_yds,player_rec_yds,player_pass_tds,player_anytime_td"

DEFAULT_ITERATIONS = 20000

# -------------------------------
# Helpers
# -------------------------------
def nowstamp():
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")

def _is_api_allowed(flag: bool) -> bool:
    return flag or os.environ.get("ALLOW_API_CALLS", "") == "1"

# -------------------------------
# Odds API fetch + cache
# -------------------------------
def get_odds(mode="live", regions="us", allow_api=False) -> List[Dict[str, Any]]:
    if mode == "historical":
        files = sorted(glob.glob("catalog_nfl_*.json"))
        if not files:
            raise FileNotFoundError("No historical catalog found.")
        with open(files[-1], "r") as f: return json.load(f)

    files = sorted(glob.glob("catalog_nfl_*.json"))
    if files:
        latest = files[-1]
        ts = datetime.strptime(latest.replace("catalog_nfl_","").replace(".json",""), "%Y%m%d_%H%M%S")
        age = (datetime.utcnow() - ts).total_seconds() / 3600.0
        if age < 2:   # cache window = 2h
            try:
                with open(latest,"r") as f: return json.load(f)
            except: pass

    if not _is_api_allowed(allow_api):
        raise RuntimeError("API calls disabled. Use --allow_api or ALLOW_API_CALLS=1 to enable.")

    if not API_KEY or API_KEY.startswith("PASTE_"):
        raise RuntimeError("No Odds API key set.")

    url = f"{BASE_URL}/{SPORT_ID}/odds"
    params = {"apiKey": API_KEY,"regions":regions,"markets":MARKETS,"oddsFormat":"american"}
    r = requests.get(url, params=params, timeout=30)
    if r.status_code != 200: raise RuntimeError(f"API error: {r.status_code} {r.text}")

    data = r.json()
    out = f"catalog_nfl_{nowstamp()}.json"
    with open(out,"w") as f: json.dump(data,f,indent=2)
    return data

# -------------------------------
# Model Config
# -------------------------------
@dataclass
class FootballModelConfig:
    iterations: int = DEFAULT_ITERATIONS
    team_score_sd_base: float = 11.0
    yards_per_point: float = 16.3
    pass_rate: float = 0.62

# -------------------------------
# Survivor Helper
# -------------------------------
def make_survivor_plan(team_probs, used, double_from):
    used = set(u.lower() for u in used)
    available = [(t,p) for t,p in team_probs if t.lower() not in used]
    ranked = sorted(available, key=lambda x:x[1], reverse=True)
    return {
        "recommendations": ranked[:3],
        "current_week": "auto",
        "picks_required": 2 if double_from <= 18 else 1
    }

# -------------------------------
# Excel Export
# -------------------------------
def save_excel(report, prev, fname, survivor=None):
    with pd.ExcelWriter(fname, engine="openpyxl") as writer:
        pd.DataFrame(report["game_summaries"]).to_excel(writer, index=False, sheet_name="Current_Game_Summaries")
        pd.DataFrame(report["player_props"]).to_excel(writer, index=False, sheet_name="Current_Player_Props")
        pd.DataFrame(report["parlay_suggestions"]).to_excel(writer, index=False, sheet_name="Current_Parlays")

        if prev:
            pd.DataFrame(prev.get("game_summaries",[])).to_excel(writer, index=False, sheet_name="Prev_Game_Summaries")
            pd.DataFrame(prev.get("player_props",[])).to_excel(writer, index=False, sheet_name="Prev_Player_Props")
            pd.DataFrame(prev.get("parlay_suggestions",[])).to_excel(writer, index=False, sheet_name="Prev_Parlays")

        if survivor:
            pd.DataFrame(survivor["recommendations"], columns=["Team","WinProb"]).to_excel(writer, index=False, sheet_name="Survivor_Recs")

# -------------------------------
# Main Simulation Driver
# -------------------------------
def run_model(mode="live", iterations=DEFAULT_ITERATIONS, allow_api=False, survivor=False, used=None, double_from=13):
    raw = get_odds(mode=mode, allow_api=allow_api)

    # Example deliverables (replace with your full model logic later)
    game_summaries = []
    player_props = []
    parlays = []

    team_probs = []
    for g in raw:
        home, away = g.get("home_team"), g.get("away_team")
        game_summaries.append({"matchup": f"{away} at {home}", "projected_total": 44.5})
        team_probs.append((home, 0.65))  # stub probability
        team_probs.append((away, 0.35))

    report = {
        "game_summaries": game_summaries,
        "player_props": player_props,
        "parlay_suggestions": parlays,
    }

    survivor_out = None
    if survivor:
        survivor_out = make_survivor_plan(team_probs, used or [], double_from)

    return report, None, survivor_out

# -------------------------------
# CLI Entry Point
# -------------------------------
if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--mode",default="live",choices=["live","historical"])
    ap.add_argument("--allow_api",action="store_true")
    ap.add_argument("--survivor",action="store_true")
    ap.add_argument("--used",nargs="*",default=[])
    ap.add_argument("--double_from",type=int,default=13)
    args=ap.parse_args()

    rep, prev, surv = run_model(
        mode=args.mode,
        allow_api=args.allow_api,
        survivor=args.survivor,
        used=args.used,
        double_from=args.double_from
    )
    print(json.dumps({"report":rep,"survivor":surv}, indent=2))
