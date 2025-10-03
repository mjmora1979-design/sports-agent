#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sports_agent.py
Multi-sport simulation agent:
- Odds API global odds + player props
- nfl_data_py historical stats (NFL/NCAAF)
- Survivor helper
- Excel export
"""

import os, json, glob, requests
from datetime import datetime, timezone, timedelta
from typing import List, Optional
import pandas as pd
import nfl_data_py as nfl

# -------------------------------
# Config
# -------------------------------
API_KEY = os.environ.get("ODDS_API_KEY", "PASTE_YOUR_API_KEY_HERE")
BASE_URL = "https://api.the-odds-api.com/v4/sports"

SPORT_MAP = {
    "nfl": "americanfootball_nfl",
    "ncaaf": "americanfootball_ncaaf",
    "nba": "basketball_nba",
    "mlb": "baseball_mlb",
    "ncaab": "basketball_ncaab"
}

FEATURED_MARKETS = "h2h,spreads,totals"
PROP_MARKETS = "player_pass_yds,player_rush_yds,player_receiving_yds,player_pass_tds,player_anytime_td"

WEEKLY_CACHE = "data/weekly_stats.csv"

# -------------------------------
# Helpers
# -------------------------------
def nowstamp() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")

def _is_api_allowed(flag: bool) -> bool:
    return flag or os.environ.get("ALLOW_API_CALLS", "") == "1"

def _parse_time(ts: str) -> datetime:
    try:
        if ts.endswith("Z"):
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return datetime.fromisoformat(ts)
    except Exception:
        return datetime.utcnow().replace(tzinfo=timezone.utc)

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
# Historical Data (NFL/NCAAF)
# -------------------------------
def update_weekly_stats(years=[2024, 2025], outpath=WEEKLY_CACHE):
    os.makedirs("data", exist_ok=True)
    df = nfl.import_weekly_data(years)
    df.to_csv(outpath, index=False)
    return df

def load_weekly_stats():
    if os.path.exists(WEEKLY_CACHE):
        mtime = datetime.fromtimestamp(os.path.getmtime(WEEKLY_CACHE))
        if (datetime.utcnow() - mtime) > timedelta(days=7):
            return update_weekly_stats()
        return pd.read_csv(WEEKLY_CACHE)
    else:
        return update_weekly_stats()

# -------------------------------
# Odds API
# -------------------------------
def get_global_odds(sport: str, allow_api: bool = False):
    sport_id = SPORT_MAP.get(sport, "americanfootball_nfl")
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
# Game Filtering
# -------------------------------
def filter_games_by_sport(raw, sport):
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    if sport in ["nfl", "ncaaf"]:
        # Next 7 days of games
        cutoff = now + timedelta(days=7)
        return [g for g in raw if _parse_time(g.get("commence_time")) <= cutoff]
    else:
        # Only today’s games
        today = now.date()
        return [g for g in raw if _parse_time(g.get("commence_time")).date() == today]

# -------------------------------
# Survivor
# -------------------------------
def make_survivor_plan(team_probs: List[tuple], used: List[str], double_from: int):
    used_set = set(u.lower() for u in (used or []))
    available = [(t, p) for t, p in team_probs if t and t.lower() not in used_set]
    ranked = sorted(available, key=lambda x: x[1], reverse=True)
    return {"recommendations": ranked[:3], "week": double_from, "used": used or []}

# -------------------------------
# Excel Export
# -------------------------------
def save_excel(report, prev, fname, survivor=None):
    with pd.ExcelWriter(fname, engine="openpyxl") as writer:
        pd.DataFrame(report).to_excel(writer, index=False, sheet_name="Games")
        if survivor:
            pd.DataFrame(survivor.get("recommendations", []), columns=["Team", "WinProb"]).to_excel(writer, index=False, sheet_name="Survivor")

# -------------------------------
# Main
# -------------------------------
def run_model(mode="live", allow_api=False, survivor=False, used=None, double_from=13, game_filter=None, max_games=None, sport="nfl"):
    raw = get_global_odds(sport, allow_api=allow_api)
    selected = filter_games_by_sport(raw, sport)

    report, team_probs = [], []

    for g in selected:
        gid, home, away = g.get("id"), g.get("home_team"), g.get("away_team")
        commence = g.get("commence_time")

        for bm in g.get("bookmakers", []):
            for mk in bm.get("markets", []):
                for o in mk.get("outcomes", []):
                    report.append({
                        "home_team": home,
                        "away_team": away,
                        "commence_time": commence,
                        "book": bm.get("title"),
                        "market": mk.get("key"),
                        "name": o.get("name"),
                        "price": o.get("price")
                    })
        # quick win prob estimate
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
            away_p = sum(p[0] for p in probs)/len(probs)
            home_p = sum(p[1] for p in probs)/len(probs)
            team_probs.append((home, home_p)); team_probs.append((away, away_p))

    surv = make_survivor_plan(team_probs, used or [], double_from) if survivor else None
    return report, None, surv
