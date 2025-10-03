import os, requests, datetime
import nfl_data_py as nfl

API_HOST = os.getenv("SPORTSBOOK_RAPIDAPI_HOST", "sportsbook-api2.p.rapidapi.com")
API_KEY = os.getenv("SPORTSBOOK_RAPIDAPI_KEY", None)
BOOKS_DEFAULT = os.getenv("BOOKS_DEFAULT", "draftkings,fanduel")

def current_week():
    """Detect current NFL week (fallback to 1)."""
    try:
        # safer fallback using nfl_data_py
        season = nfl.current_year()
        sched = nfl.import_schedules([season])
        today = datetime.date.today()
        sched["gameday"] = sched["gameday"].astype(str)
        for wk in sorted(sched["week"].unique()):
            week_games = sched[sched["week"] == wk]
            dates = [datetime.date.fromisoformat(d) for d in week_games["gameday"] if d != "nan"]
            if dates and min(dates) <= today <= max(dates):
                return int(wk)
    except Exception as e:
        print("[WARN] Week detection failed, fallback:", e)
    return 1

def get_odds(sport="nfl", region="us", markets=None, books=None):
    """Fetch odds from RapidAPI sportsbook."""
    url = f"https://{API_HOST}/v1/odds"   # <-- FIXED ENDPOINT
    params = {
        "sport": sport,
        "region": region,
        "mkt": markets or "h2h,spreads,totals,player_props",
        "oddsFormat": "american",
        "bookmakers": books or BOOKS_DEFAULT,
    }
    headers = {"X-RapidAPI-Host": API_HOST}
    if API_KEY:
        headers["X-RapidAPI-Key"] = API_KEY

    print("[DEBUG] Requesting odds from:", url)
    print("[DEBUG] Params:", params)
    print("[DEBUG] Headers (key hidden):", {k: ("***" if "Key" in k else v) for k, v in headers.items()})

    try:
        r = requests.get(url, headers=headers, params=params, timeout=20)
        print("[DEBUG] Response status:", r.status_code)
        if r.status_code != 200:
            print("[DEBUG] Response text:", r.text)
            return {"status": "error", "games": [], "message": r.text}
        data = r.json()
        return {"status": "success", "games": data.get("games", [])}
    except Exception as e:
        print("[ERROR] Odds request failed:", e)
        return {"status": "error", "games": [], "message": str(e)}

def rows_for_sheets(games, week):
    """Flatten games for Sheets logging."""
    rows = []
    for g in games:
        home = g.get("home_team")
        away = g.get("away_team")
        commence = g.get("commence_time")
        markets = [m["key"] for m in g.get("markets", [])] if "markets" in g else []
        rows.append([week, home, away, commence, ",".join(markets)])
    return rows
