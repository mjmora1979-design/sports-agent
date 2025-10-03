#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sports_agent.py
Multi-sport simulation agent:
- Odds API global odds + player props
- nfl_data_py historical stats (NFL only)
- Survivor helper (NFL)
- Excel export
"""

import os, json, glob
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd, requests
import nfl_data_py as nfl

# -------------------------------
# Config
# -------------------------------
API_KEY = os.environ.get("ODDS_API_KEY", "PASTE_YOUR_API_KEY_HERE")
BASE_URL = "https://api.the-odds-api.com/v4/sports"

# Sports map (keys must match Odds API)
SPORTS = {
    "nfl": "americanfootball_nfl",
    "ncaaf": "americanfootball_ncaaf",
    "nba": "basketball_nba",
    "ncaab": "basketball_ncaab",
    "mlb": "baseball_mlb"
}

FEATURED_MARKETS = "h2h,spreads,totals"
PROP_MARKETS = "player_pass_yds,player_rush_yds,player_receiving_yds,player_pass_tds,player_anytime_td"

DEFAULT_ITERATIONS = 20000
DEFAULT_MAX_GAMES = None

AZ_CO_TEAMS = ["Arizona Cardinals", "Denver Broncos"]
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
# Historical Data (NFL only)
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

def project_from_history(player: str, market: str, df: pd.DataFrame):
    try:
        pstats = df[df["player_display_name"].str.lower() == player.lower()]
        if pstats.empty: return None
        if "pass_yds" in market: return pstats["passing_yards"].mean()
        if "rush_yds" in market: return pstats["rushing_yards"].mean()
        if "receiving_yds" in market: return pstats["receiving_yards"].mean()
        if "pass_tds" in market: return pstats["passing_tds"].mean()
        if "anytime_td" in market:
            td_games = (pstats["rushing_tds"] + pstats["receiving_tds"]) > 0
            return td_games.mean()
    except Exception:
        return None
    return None

def adjust_with_haircut(proj: float, injury_flag=False) -> float:
    if proj is None: return None
    factor = 0.8
    if injury_flag: factor = 0.7
    return proj * factor

# -------------------------------
# Odds API
# -------------------------------
def get_global_odds(allow_api: bool = False, sport_id: str = "americanfootball_nfl"):
    files = sorted(glob.glob(f"catalog_{sport_id}_*.json"))
    if files:
        latest = files[-1]
        ts = datetime.strptime(latest.split("_")[-1].replace(".json", ""), "%Y%m%d_%H%M%S")
        age_hours = (datetime.utcnow() - ts).total_seconds() / 3600.0
        if age_hours < 2:
            return json.load(open(latest, "r"))

    if not _is_api_allowed(allow_api):
        raise RuntimeError("API disabled")
    if not API_KEY or API_KEY.startswith("PASTE_"):
        raise RuntimeError("No API key set")

    url = f"{BASE_URL}/{sport_id}/odds"
    params = {
        "apiKey": API_KEY,
        "regions": "us",
        "markets": FEATURED_MARKETS,
        "oddsFormat": "american"
    }

    # NFL and NCAAF → pull full week
    if sport_id in ["americanfootball_nfl", "americanfootball_ncaaf"]:
        params["daysFrom"] = 7

    r = requests.get(url, params=params, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"API error {r.status_code} {r.text}")
    data = r.json()
    json.dump(data, open(f"catalog_{sport_id}_{nowstamp()}.json", "w"), indent=2)
    return data

def get_event_props(event_id: str, allow_api: bool = False, sport_id: str = "americanfootball_nfl"):
    if not _is_api_allowed(allow_api): return []
    if not API_KEY or API_KEY.startswith("PASTE_"): return []
    url = f"{BASE_URL}/{sport_id}/events/{event_id}/odds"
    params = {"apiKey": API_KEY, "regions": "us", "markets": PROP_MARKETS, "oddsFormat": "american"}
    r = requests.get(url, params=params, timeout=30)
    if r.status_code != 200: return []
    return r.json()

# -------------------------------
# Survivor
# -------------------------------
def make_survivor_plan(team_probs: List[tuple], used: List[str], double_from: int):
    used_set = set(u.lower() for u in (used or []))
    available = [(t, p) for t, p in team_probs if t and t.lower() not in used_set]
    ranked = sorted(available, key=lambda x: x[1], reverse=True)
    return {
        "recommendations": ranked[:3],
        "current_week": "auto",
        "picks_required": 2 if double_from <= 18 else 1,
        "used": used,
        "week": double_from
    }

# -------------------------------
# Excel Export
# -------------------------------
def save_excel(report, prev, fname, survivor=None):
    with pd.ExcelWriter(fname, engine="openpyxl") as writer:
        pd.DataFrame(report).to_excel(writer, index=False, sheet_name="Odds_Report")
        if survivor:
            pd.DataFrame(survivor.get("recommendations", []), columns=["Team", "WinProb"]).to_excel(
                writer, index=False, sheet_name="Survivor_Recs"
            )

# -------------------------------
# Main
# -------------------------------
def run_model(mode="live", iterations=DEFAULT_ITERATIONS, allow_api=False,
              survivor=False, used=None, double_from=13, game_filter=None,
              max_games=DEFAULT_MAX_GAMES, sport="nfl"):
    sport_id = SPORTS.get(sport.lower(), "americanfootball_nfl")
    raw = get_global_odds(allow_api=allow_api, sport_id=sport_id)

    report, team_probs = [], []
    df_stats = load_weekly_stats() if sport == "nfl" else None

    for g in raw:
        gid, home, away = g.get("id"), g.get("home_team"), g.get("away_team")
        for bm in g.get("bookmakers", []):
            for mk in bm.get("markets", []):
                for o in mk.get("outcomes", []):
                    entry = {
                        "home_team": home,
                        "away_team": away,
                        "commence_time": g.get("commence_time"),
                        "book": bm.get("title"),
                        "market": mk.get("key"),
                        "name": o.get("name"),
                        "price": o.get("price"),
                    }
                    report.append(entry)

        # Survivor win prob (NFL only)
        probs = []
        if sport == "nfl":
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
                team_probs.append((home, home_p))
                team_probs.append((away, away_p))

    surv = make_survivor_plan(team_probs, used or [], double_from) if (sport == "nfl" and survivor) else None
    return report, None, surv
