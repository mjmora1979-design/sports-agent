# sports_agent.py
# Sport scope logic, odds normalization, props handling, summary building, Excel export.

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
import pandas as pd
import io

from sportsbook_api import get_events_with_odds, PROP_MARKET_MAP
from sheets_writer import log_batch

BOOKS_WANTED = ["draftkings","fanduel"]  # server param, normalized later

# -------- Time Helpers --------
def _utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")

def _start_end_for_scope(sport: str) -> Dict[str,str]:
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    if sport in ("nfl","ncaaf"):
        start = now
        end = now + timedelta(days=8)   # full upcoming week
        return {"start": _utc_iso(start), "end": _utc_iso(end), "week": _approx_week_number(start)}
    else:
        start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
        end = start + timedelta(days=1) - timedelta(seconds=1)  # today
        return {"start": _utc_iso(start), "end": _utc_iso(end), "week": None}

def _approx_week_number(dt_utc: datetime) -> Optional[int]:
    # Placeholder: use ISO week number unless API provides official week
    return int(dt_utc.isocalendar()[1])

# -------- Odds Utilities --------
def _pick_best_price(entries: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not entries: return None
    # Ranking: prefer higher positive odds, else the least negative (better for bettor)
    def score(e):
        p = e.get("price")
        if p is None: return -1e9
        if p >= 0: return 100 + p
        else: return 100 - abs(p)
    return sorted(entries, key=score, reverse=True)[0]

def _summarize_game(game: Dict[str, Any]) -> Dict[str, Any]:
    by_team_ml, spread_best, total_best = {}, {}, {}
    team_names = [game.get("home_team"), game.get("away_team")]

    ml_entries_by_team = {t: [] for t in team_names if t}
    spread_entries_by_team = {t: [] for t in team_names if t}
    total_entries = {"Over": [], "Under": []}

    for bookname, data in game.get("books", {}).items():
        # Moneyline
        for t in team_names:
            if t in (data.get("h2h") or {}) and data["h2h"][t] is not None:
                ml_entries_by_team[t].append({"book": bookname, "price": data["h2h"][t]})
        # Spreads
        for sp in data.get("spreads", []):
            spread_entries_by_team.get(sp.get("name",""), []).append({
                "book": bookname, "price": sp.get("price"), "point": sp.get("point")
            })
        # Totals
        for side in ("Over","Under"):
            if side in (data.get("totals") or {}) and data["totals"][side].get("price") is not None:
                total_entries[side].append({
                    "book": bookname, "price": data["totals"][side]["price"], "point": data["totals"][side].get("point")
                })

    for t, entries in ml_entries_by_team.items():
        bp = _pick_best_price(entries)
        if bp: by_team_ml[t] = {"book": bp["book"], "price": bp["price"]}

    for t, entries in spread_entries_by_team.items():
        bp = _pick_best_price(entries)
        if bp: spread_best[t] = {"book": bp["book"], "price": bp["price"], "point": bp.get("point")}

    for side, entries in total_entries.items():
        bp = _pick_best_price(entries)
        if bp: total_best[side] = {"book": bp["book"], "price": bp["price"], "point": bp.get("point")}

    return {
        "best_moneyline_by_team": by_team_ml,
        "best_spread_by_team": spread_best,
        "best_total": total_best
    }

# -------- Normalization --------
def _normalize_books_struct(provider_event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize provider event into:
      books: {
        "DraftKings": {"h2h": {...}, "spreads": [...], "totals": {...}, "props": {...}},
        "FanDuel": {...}
      }
    """
    out = {}
    for b in provider_event.get("books", []):
        book_name = b.get("name") or b.get("book") or ""
        if "draft" in book_name.lower():
            key = "DraftKings"
        elif "fan" in book_name.lower():
            key = "FanDuel"
        else:
            continue

        entry = {"h2h": {}, "spreads": [], "totals": {}, "props": {}}

        # Moneyline
        for ml in b.get("moneyline", []) or b.get("h2h", []):
            name, price = ml.get("name"), ml.get("price")
            if name and price is not None:
                entry["h2h"][name] = price

        # Spreads
        for sp in b.get("spreads", []):
            nm, pt, pr = sp.get("name"), sp.get("point"), sp.get("price")
            if nm and pt is not None and pr is not None:
                entry["spreads"].append({"name": nm, "point": pt, "price": pr})

        # Totals
        tot = b.get("totals")
        if isinstance(tot, dict):
            entry["totals"] = {}
            for side in ("Over","Under"):
                sdata = tot.get(side) or tot.get(side.lower())
                if sdata and sdata.get("price") is not None:
                    entry["totals"][side] = {"point": sdata.get("point"), "price": sdata.get("price")}

        # Props (normalize best-effort)
        props, normalized_props = b.get("props") or {}, {}
        def add_prop(cat_key, raw):
            if not raw: return
            by_player = {}
            for item in raw:
                pl = item.get("player") or item.get("name")
                if not pl: continue
                by_player[pl] = {}
                if item.get("line") is not None: by_player[pl]["line"] = item["line"]
                if item.get("price") is not None: by_player[pl]["price"] = item["price"]
            if by_player: normalized_props[cat_key] = by_player

        for ours, prov in PROP_MARKET_MAP.items():
            raw = props.get(prov) or b.get(prov)
            if raw:
                key = ours.replace("player_", "").replace("_yds","_yds").replace("_tds","_tds").replace("_anytime_","_")
                add_prop(key, raw)

        entry["props"] = normalized_props
        out[key] = entry
    return out

# -------- Build Payload --------
def build_payload(sport: str, allow_api: bool, game_filter: Optional[str] = None, max_games: Optional[int] = None) -> Dict[str, Any]:
    sc = _start_end_for_scope(sport)
    start_iso, end_iso, approx_week = sc["start"], sc["end"], sc["week"]

    wanted_props = ["player_pass_yds", "player_rush_yds", "player_receiving_yds", "player_anytime_td", "player_pass_tds"]
    include_props = sport in ("nfl","ncaaf")

    provider_json = {"events": []}
    if allow_api:
        provider_json = get_events_with_odds(
            sport=sport, start_iso=start_iso, end_iso=end_iso,
            include_props=include_props, wanted_prop_keys=wanted_props,
            wanted_books=BOOKS_WANTED, odds_format="american"
        )

    games_out, sheets_rows = [], []
    for ev in provider_json.get("events", []):
        home = ev.get("home_team") or ev.get("home") or ev.get("homeName")
        away = ev.get("away_team") or ev.get("away") or ev.get("awayName")
        commence_iso = ev.get("commence_time") or ev.get("start_time") or ev.get("startTime")
        event_id = ev.get("id") or ev.get("event_id") or ev.get("key")

        books_norm = _normalize_books_struct(ev)
        game_obj = {
            "home_team": home,
            "away_team": away,
            "commence_time": commence_iso,
            "books": books_norm
        }
        game_obj["summary"] = _summarize_game({
            "home_team": home,
            "away_team": away,
            "books": books_norm
        })

        # Flatten for Sheets logging
        for bookname, data in books_norm.items():
            for t, price in (data.get("h2h") or {}).items():
                sheets_rows.append({
                    "event_id": event_id, "commence_time": commence_iso,
                    "home": home, "away": away, "book": bookname,
                    "market": "moneyline", "label": t, "price": price, "point_or_line": ""
                })
            for sp in data.get("spreads") or []:
                sheets_rows.append({
                    "event_id": event_id, "commence_time": commence_iso,
                    "home": home, "away": away, "book": bookname,
                    "market": "spread", "label": sp.get("name"), "price": sp.get("price"), "point_or_line": sp.get("point")
                })
            for side in ("Over","Under"):
                tots = data.get("totals") or {}
                if side in tots:
                    sheets_rows.append({
                        "event_id": event_id, "commence_time": commence_iso,
                        "home": home, "away": away, "book": bookname,
                        "market": f"total_{side.lower()}", "label": side,
                        "price": tots[side].get("price"), "point_or_line": tots[side].get("point")
                    })
            for cat, players in (data.get("props") or {}).items():
                for player, pv in players.items():
                    sheets_rows.append({
                        "event_id": event_id, "commence_time": commence_iso,
                        "home": home, "away": away, "book": bookname,
                        "market": f"prop_{cat}", "label": player,
                        "price": pv.get("price"), "point_or_line": pv.get("line")
                    })

        games_out.append(game_obj)

    # Filter + limit
    if game_filter:
        gf = game_filter.lower()
        games_out = [g for g in games_out if gf in (g.get("home_team","")+g.get("away_team","")).lower()]
    if max_games is not None and max_games > 0:
        games_out = games_out[:max_games]

    # Sheets logging (only if enabled and allow_api)
    if allow_api and sheets_rows:
        log_batch(sport, sheets_rows)

    return {
        "status": "success",
        "week": approx_week if sport in ("nfl","ncaaf") else None,
        "games": games_out,
        "survivor": {"used": [], "week": approx_week if sport in ("nfl","ncaaf") else None}
    }

# -------- Excel Export --------
def to_excel(payload: Dict[str, Any]) -> bytes:
    games_rows, surv_rows = [], []
    for g in payload.get("games", []):
        row = {
            "commence_time": g.get("commence_time"),
            "home_team": g.get("home_team"),
            "away_team": g.get("away_team"),
        }
        s = g.get("summary", {})
        for team, v in (s.get("best_moneyline_by_team") or {}).items():
            row[f"best_ml_{team}"] = f"{v.get('book')} {v.get('price')}"
        for side, v in (s.get("best_total") or {}).items():
            row[f"best_total_{side}"] = f"{v.get('book')} {v.get('price')} @ {v.get('point')}"
        games_rows.append(row)

    surv = payload.get("survivor") or {}
    surv_rows.append({"week": surv.get("week"), "used_csv": ",".join(surv.get("used") or [])})

    df_games, df_surv = pd.DataFrame(games_rows), pd.DataFrame(surv_rows)
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="xlsxwriter") as xl:
        df_games.to_excel(xl, sheet_name="games", index=False)
        df_surv.to_excel(xl, sheet_name="survivor", index=False)
    return bio.getvalue()
