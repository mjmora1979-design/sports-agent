#!/usr/bin/env python3

# -*- coding: utf-8 -*-

"""

sports_agent.py (MVP updated)

NFL simulation agent:

- Game lines + props (Odds API or cached JSON)

- Synthetic odds if real odds missing

- Survivor helper

- Excel export

"""

import os, json, glob, argparse, traceback

from datetime import datetime, timezone, timedelta

from typing import Dict, List, Any, Optional

import pandas as pd, requests

import nfl_data_py as nfl

import math

# -------------------------------

# Config

# -------------------------------

API_KEY = os.environ.get("ODDS_API_KEY", "PASTE_YOUR_API_KEY_HERE")

BASE_URL = "https://api.the-odds-api.com/v4/sports"

SPORT_ID = "americanfootball_nfl"

FEATURED_MARKETS = "h2h,spreads,totals"

PROP_MARKETS = "player_pass_yds,player_rush_yds,player_receiving_yds,player_pass_tds,player_anytime_td"

DEFAULT_ITERATIONS = 20000

DEFAULT_MAX_GAMES = None   # None = all games

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

def safe_float(x):

    try: return float(x)

    except: return None

# -------------------------------

# Synthetic odds generator

# -------------------------------

def synthetic_odds_from_line(line: float, proj: float, std_dev: float = 1.5):

    """

    Build synthetic probabilities/odds from model projection vs line.

    """

    if line is None or proj is None: 

        return None

    try:

        z = (proj - line) / std_dev

        # Simple sigmoid as prob approximation

        prob_over = 1 / (1 + math.exp(-z))

        prob_under = 1 - prob_over

        def prob_to_odds(p):

            if p <= 0 or p >= 1: return None

            return round(-100 * p / (1 - p)) if p > 0.5 else round(100 * (1 - p) / p)

        return {

            "prob_over": round(prob_over, 3),

            "prob_under": round(prob_under, 3),

            "fair_odds_over": prob_to_odds(prob_over),

            "fair_odds_under": prob_to_odds(prob_under),

        }

    except Exception as e:

        print("Synthetic odds error:", e)

        return None

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

    factor = 0.8 if not injury_flag else 0.7

    return proj * factor

# -------------------------------

# Odds API (with fallback)

# -------------------------------

def get_global_odds(allow_api: bool = False):

    """

    Fetch NFL odds/lines from Odds API (DraftKings only).

    Falls back to cached JSON if API fails or disabled.

    """

    files = sorted(glob.glob("catalog_global_nfl_*.json"))

    if _is_api_allowed(allow_api):

        try:

            if not API_KEY or API_KEY.startswith("PASTE_"):

                raise RuntimeError("No API key set")

            url = f"{BASE_URL}/{SPORT_ID}/odds"

            params = {

                "apiKey": API_KEY,

                "regions": "us",

                "markets": FEATURED_MARKETS,

                "oddsFormat": "american",

                "bookmakers": "DraftKings"

            }

            r = requests.get(url, params=params, timeout=30)

            if r.status_code == 200:

                data = r.json()

                fname = f"catalog_global_nfl_{nowstamp()}.json"

                with open(fname, "w") as f:

                    json.dump(data, f, indent=2)

                return data

            else:

                raise RuntimeError(f"API error {r.status_code} {r.text}")

        except Exception as e:

            print("Live API fetch failed, falling back to cache:", e)

            traceback.print_exc()

    if files:

        return json.load(open(files[-1], "r"))

    raise RuntimeError("No odds data available (API disabled and no cache)")

def get_event_props(event_id: str, allow_api: bool = False):

    if not _is_api_allowed(allow_api): return []

    if not API_KEY or API_KEY.startswith("PASTE_"): return []

    url = f"{BASE_URL}/{SPORT_ID}/events/{event_id}/odds"

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

    return {"recommendations": ranked[:3], "current_week": "auto", "picks_required": 2 if double_from <= 18 else 1}

# -------------------------------

# Excel Export

# -------------------------------

def save_excel(report, prev, fname, survivor=None):

    with pd.ExcelWriter(fname, engine="openpyxl") as writer:

        pd.DataFrame(report.get("game_summaries", [])).to_excel(writer, index=False, sheet_name="Current_Game_Summaries")

        pd.DataFrame(report.get("player_props", [])).to_excel(writer, index=False, sheet_name="Current_Player_Props")

        pd.DataFrame(report.get("parlay_suggestions", [])).to_excel(writer, index=False, sheet_name="Current_Parlays")

        pd.DataFrame(report.get("audit", [])).to_excel(writer, index=False, sheet_name="Audit")

        if survivor:

            pd.DataFrame(survivor.get("recommendations", []), columns=["Team", "WinProb"]).to_excel(writer, index=False, sheet_name="Survivor_Recs")

# -------------------------------

# Main

# -------------------------------

def run_model(mode="live", iterations=DEFAULT_ITERATIONS, allow_api=False, survivor=False, used=None, double_from=13, game_filter=None, max_games=DEFAULT_MAX_GAMES):

    df_stats = load_weekly_stats()

    raw = get_global_odds(allow_api=allow_api)

    selected = []

    for g in raw:

        if g.get("home_team") in AZ_CO_TEAMS or g.get("away_team") in AZ_CO_TEAMS:

            if g not in selected: selected.append(g)

    sorted_raw = sorted(raw, key=lambda g: _parse_time(g.get("commence_time", nowstamp())))

    for g in sorted_raw:

        if g not in selected: selected.append(g)

    if game_filter:

        for g in raw:

            combined = (g.get("home_team","")+g.get("away_team","")).lower()

            if game_filter.lower() in combined and g not in selected:

                selected.append(g)

    game_summaries, player_props, team_probs = [], [], []

    for g in selected:

        gid, home, away = g.get("id"), g.get("home_team"), g.get("away_team")

        # win prob

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

        else:

            away_p, home_p = 0.5, 0.5

        game_summaries.append({"matchup": f"{away} at {home}", "market_win_prob_home": round(home_p,3), "market_win_prob_away": round(away_p,3)})

        team_probs.append((home, home_p)); team_probs.append((away, away_p))

        # props

        ev = get_event_props(gid, allow_api=allow_api)

        for ed in ev:

            for bm in ed.get("bookmakers", []):

                for mk in bm.get("markets", []):

                    for outcome in mk.get("outcomes", []):

                        name, line, price = outcome.get("name"), outcome.get("line"), outcome.get("price")

                        model_proj = project_from_history(name, mk.get("key"), df_stats)

                        adj_proj = adjust_with_haircut(model_proj)

                        prop_dict = {

                            "matchup": f"{away} at {home}",

                            "player": name,

                            "market": mk.get("key"),

                            "market_line": safe_float(line),

                            "model_proj": model_proj,

                            "adj_proj": adj_proj

                        }

                        # synthetic odds supplement

                        syn = synthetic_odds_from_line(safe_float(line), adj_proj)

                        if syn: prop_dict.update(syn)

                        player_props.append(prop_dict)

    report = {"game_summaries": game_summaries,"player_props": player_props,"parlay_suggestions": [],"audit":[{"timestamp_utc":datetime.utcnow().isoformat(),"selected_games":len(selected)}]}

    surv = make_survivor_plan(team_probs, used or [], double_from) if survivor else None

    return report, None, surv
 
