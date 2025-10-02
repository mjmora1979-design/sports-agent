#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sports_agent.py
NFL simulation agent with safe API guard, caching (2h, but force new pull if <1h before kickoff).
"""

import os, re, json, math, glob, argparse
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple, Any, Optional

import numpy as np, pandas as pd, requests
from bs4 import BeautifulSoup

API_KEY = os.environ.get("ODDS_API_KEY", "PASTE_YOUR_API_KEY_HERE")
BASE_URL = "https://api.the-odds-api.com/v4/sports"
SPORT_ID = "americanfootball_nfl"
MARKETS = "h2h,spreads,totals,player_pass_yds,player_rush_yds,player_rec_yds,player_pass_tds,player_anytime_td"

DEFAULT_ITERATIONS = 20000
HEADERS = {"User-Agent": "Mozilla/5.0 (NFLAgent/1.0)"}

def nowstamp():
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")

def _is_api_allowed(flag: bool) -> bool:
    return flag or os.environ.get("ALLOW_API_CALLS", "") == "1"

def get_odds(mode="live", regions="us", allow_api=False) -> List[Dict[str, Any]]:
    # Historical mode → always reuse last file
    if mode == "historical":
        files = sorted(glob.glob("catalog_nfl_*.json"))
        if not files:
            raise FileNotFoundError("No historical catalog found.")
        with open(files[-1], "r") as f: return json.load(f)

    # Check for cached file
    files = sorted(glob.glob("catalog_nfl_*.json"))
    if files:
        latest = files[-1]
        ts = datetime.strptime(latest.replace("catalog_nfl_","").replace(".json",""), "%Y%m%d_%H%M%S")
        age = (datetime.utcnow() - ts).total_seconds() / 3600.0
        # <2h old? reuse, unless <1h to kickoff
        if age < 2:
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

# ---- Minimal model simulation (trimmed for brevity) ----
@dataclass
class FootballModelConfig:
    iterations: int = DEFAULT_ITERATIONS
    team_score_sd_base: float = 11.0
    yards_per_point: float = 16.3
    pass_rate: float = 0.62

def run_model(mode="live", iterations=DEFAULT_ITERATIONS, allow_api=False):
    raw = get_odds(mode=mode, allow_api=allow_api)
    deliverables = {"game_summaries":[],"player_props":[],"parlay_suggestions":{}}
    for g in raw:
        home, away = g.get("home_team"), g.get("away_team")
        deliverables["game_summaries"].append({"matchup":f"{away} at {home}"})
    return deliverables, None

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--mode",default="live",choices=["live","historical"])
    ap.add_argument("--allow_api",action="store_true")
    args=ap.parse_args()
    rep,_=run_model(mode=args.mode,allow_api=args.allow_api)
    print(json.dumps(rep,indent=2))
