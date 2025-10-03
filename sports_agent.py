#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sports_agent.py
Multi-sport simulation agent:
- Odds API global odds + props
- nfl_data_py historical stats (for NFL)
- Survivor helper
- Excel export
"""

import os, json, glob, requests, datetime
from typing import List, Optional
import pandas as pd
import nfl_data_py as nfl

# -------------------------------
# Config
# -------------------------------
API_KEY = os.environ.get("ODDS_API_KEY", "PASTE_YOUR_API_KEY_HERE")
BASE_URL = "https://api.the-odds-api.com/v4/sports"

FEATURED_MARKETS = "h2h,spreads,totals"
PROP_MARKETS = "player_pass_yds,player_rush_yds,player_receiving_yds,player_pass_tds,player_anytime_td"

DEFAULT_ITERATIONS = 20000
DEFAULT_MAX_GAMES = None   # None = all games

SPORT_IDS = {
    "nfl": "americanfootball_nfl",
    "ncaaf": "americanfootball_ncaaf",
    "nba": "basketball_nba",
    "mlb": "baseball_mlb",
    "ncaab": "basketball_ncaab"
}

WEEKLY_CACHE = "data/weekly_stats.csv"

# -------------------------------
# Helpers
# -------------------------------
def nowstamp() -> str:
    return datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")

def _is_api_allowed(flag: bool) -> bool:
    return flag or os.environ.get("ALLOW_API_CALLS", "") == "1"

def _parse_time(ts: str) -> datetime.datetime:
    try:
        if ts.endswith("Z"):
            return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return datetime.datetime.fromisoformat(ts)
    except Exception:
        return datetime.datetime.utcnow()

def american_to_prob(odds: float) -> Optional[float]:
    if odds is None: return None
    try: odds = float(odds)
    except Exception: return None
    if odds >= 100: return 100.0 / (odds + 100.0)
    if odds <= -100: return -odds / (-odds + 100.0)
    return None

def devig_two_way(p1: float, p2: float) -> Optional[tuple]:
    if p1 is None or p2 is None: return None
    s = p1 + p2
    if s <= 0: return None
    return p1 / s, p2 / s

# -------------------------------
# Historical Data (nfl_data_py)
# -------------------------------
def update_weekly_stats(years=[2024, 2025], outpath=WEEKLY_CACHE):
    os.makedirs("data", exist_ok=True)
    df = nfl.import_weekly_data(years)
    df.to_csv(outpath, index=False)
    return df

def load_weekly_stats():
    if os.path.exists(WEEKLY_CACHE):
        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(WEEKLY_CACHE))
        if (datetime.datetime.utcnow() - mtime) > datetime.timedelta(days=7):
            return update_weekly_stats()
        return pd.read_csv(WEEKLY_CACHE)
    else:
        return update_weekly_stats()

# -------------------------------
# Odds API
# -------------------------------
def get_global_odds(allow_api: bool = False, sport_id: str = SPORT_IDS["nfl"]):
    if not _is_api_allowed(allow_api):
        raise RuntimeError("API disabled")
    if not API_KEY or API_KEY.startswith("PASTE_"):
        raise RuntimeError("No API key set")

    url = f"{BASE_URL}/{sport_id}/odds"
    params = {"apiKey": API_KEY, "regions": "us", "markets": FEATURED_MARKETS, "oddsFormat": "american"}
    r = requests.get(url, params=params, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"API error {r.status_code} {r.text}")
    return r.json()

# -------------------------------
# Survivor
# -------------------------------
def make_survivor_plan(team_probs: List[tuple], used: List[str], double_from: int):
    used_set = set(u.lower() for u in (used or []))
    available = [(t, p) for t, p in team_probs if t and t.lower() not in used_set]
    ranked = sorted(available, key=lambda x: x[1], reverse=True)
    return {"recommendations": ranked[:3], "used": used, "week": double_from}

# -------------------------------
# Excel Export
# -------------------------------
def save_excel(report, prev, fname, survivor=None):
    with pd.ExcelWriter(fname, engine="openpyxl") as writer:
        pd.DataFrame(report).to_excel(writer, index=False, sheet_name="Report")
        if survivor:
            pd.DataFrame(survivor.get("recommendations", []), columns=["Team", "WinProb"]).to_excel(
                writer, index=False, sheet_name="Survivor_Recs"
            )

# -------------------------------
# Main
# -------------------------------
def run_model(mode="live", iterations=DEFAULT_ITERATIONS, allow_api=False,
              survivor=False, used=None, double_from=13,
              game_filter=None, max_games=DEFAULT_MAX_GAMES, sport="nfl"):

    sport_id = SPORT_IDS.get(sport.lower(), SPORT_IDS["nfl"])
    raw = get_global_odds(allow_api=allow_api, sport_id=sport_id)

    today = datetime.datetime.utcnow()

    # Expand date windows
    if sport.lower() in ["nfl", "ncaaf"]:
        start_date = today - datetime.timedelta(days=2)
        end_date = today + datetime.timedelta(days=14)
    else:
        start_date = today - datetime.timedelta(hours=12)
        end_date = today + datetime.timedelta(days=1)

    # Filter games by window
    selected = []
    for g in raw:
        gtime = _parse_time(g.get("commence_time"))
        if start_date <= gtime <= end_date:
            if game_filter:
                combined = (g.get("home_team", "") + g.get("away_team", "")).lower()
                if game_filter.lower() not in combined:
                    continue
            selected.append({
                "home_team": g.get("home_team"),
                "away_team": g.get("away_team"),
                "commence_time": g.get("commence_time"),
                "book": g["bookmakers"][0]["title"] if g.get("bookmakers") else None,
                "market": g["bookmakers"][0]["markets"][0]["key"] if g.get("bookmakers") else None,
                "name": g["bookmakers"][0]["markets"][0]["outcomes"][0]["name"] if g.get("bookmakers") else None,
                "price": g["bookmakers"][0]["markets"][0]["outcomes"][0]["price"] if g.get("bookmakers") else None,
            })

    # Survivor prep (only NFL/NCAAF where win probs matter)
    team_probs = []
    for g in raw:
        home, away = g.get("home_team"), g.get("away_team")
        probs = []
        for bm in g.get("bookmakers", []):
            for mk in bm.get("markets", []):
                if mk.get("key") == "h2h":
                    pa = ph = None
                    for o in mk.get("outcomes", []):
                        if o["name"] == away: pa = american_to_prob(o["price"])
                        if o["name"] == home: ph = american_to_prob(o["price"])
                    dv = devig_two_way(pa, ph)
                    if dv: probs.append(dv)
        if probs:
            away_p = sum(p[0] for p in probs) / len(probs)
            home_p = sum(p[1] for p in probs) / len(probs)
            team_probs.append((home, home_p))
            team_probs.append((away, away_p))

    surv = make_survivor_plan(team_probs, used or [], double_from) if survivor else {"used": used or [], "week": double_from}

    return {"report": selected, "status": "success"}, None, surv
